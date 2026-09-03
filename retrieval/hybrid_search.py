"""
T-3.1-T-3.5 wired together: the single retrieval entry point Phase 4
(generation/grading) and T-3.6 (the retrieval harness) both call.

Pipeline, in order (each step is its own tested module -- this file is
composition, not new logic):
  1. BM25 search + vector search, each over the full candidate pool
     (candidate_k -- deliberately large; the corpus is 84 units, so
     "search everything, filter after" is cheap and never truncates a
     result the later filters would have kept).
  2. T-3.1 Reciprocal Rank Fusion over the two rankings.
  3. T-3.2 hard filters (country, jurisdiction_scope) on the fused order.
  4. T-3.3 as-of-date resolution against effective_date (Finding 2).
  5. T-3.4 lineage dedup (FM-D6), applied to whatever survives 3-4.
  6. Truncate to rerank_candidate_k, then T-3.5 FlashRank rerank.
  7. Truncate to top_k.

Steps 3 and 4 filter a SET (order doesn't matter, they only decide
membership); the fused rank order from step 2 is what determines each
kept piece's position before rerank.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from ingestion.index_units import IndexableUnit
from ingestion.logging_setup import get_logger
from retrieval.bm25_index import BM25Index
from retrieval.filters import apply_hard_filters, dedup_by_lineage, select_current_as_of
from retrieval.fusion import DEFAULT_RRF_K, reciprocal_rank_fusion
from retrieval.reranker import Reranker
from retrieval.vector_index import VectorIndex

_log = get_logger("retrieval.hybrid_search")


@dataclass
class RetrievedPiece:
    piece_id: str
    clause_id: str
    text: str
    fused_score: float
    rerank_score: float | None
    unit: IndexableUnit


class HybridRetriever:
    def __init__(self, bm25_index: BM25Index, vector_index: VectorIndex, units: list[IndexableUnit]):
        self._bm25 = bm25_index
        self._vector = vector_index
        self._units_by_piece_id: dict[str, IndexableUnit] = {u.piece_id: u for u in units}
        self._text_by_piece_id: dict[str, str] = {u.piece_id: u.text for u in units}

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        country: str | None = None,
        jurisdiction_scope: str | None = None,
        as_of_date: dt.date | None = None,
        reranker: Reranker | None = None,
        rrf_k: int = DEFAULT_RRF_K,
        rerank_candidate_k: int = 20,
    ) -> list[RetrievedPiece]:
        if as_of_date is None:
            as_of_date = dt.date.today()

        candidate_k = len(self._units_by_piece_id)
        bm25_ranked = [r.piece_id for r in self._bm25.search(query, top_k=candidate_k)]
        vector_ranked = [r["piece_id"] for r in self._vector.search(query, top_k=candidate_k)]
        fused_scores = reciprocal_rank_fusion([bm25_ranked, vector_ranked], k=rrf_k)
        fused_order = sorted(fused_scores, key=lambda pid: (-fused_scores[pid], pid))

        all_units = list(self._units_by_piece_id.values())
        allowed_units = apply_hard_filters(all_units, country=country, jurisdiction_scope=jurisdiction_scope)
        allowed_units = select_current_as_of(allowed_units, as_of_date)
        allowed_ids = {u.piece_id for u in allowed_units}

        filtered_order = [pid for pid in fused_order if pid in allowed_ids]
        deduped_order = dedup_by_lineage(filtered_order, self._units_by_piece_id)

        pre_rerank = deduped_order[: max(top_k, rerank_candidate_k)]

        if reranker is not None and pre_rerank:
            candidates = [(pid, self._text_by_piece_id[pid]) for pid in pre_rerank]
            reranked = reranker.rerank(query, candidates)
            rerank_score_by_id = {pid: score for pid, score in reranked}
            final_order = [pid for pid, _ in reranked]
        else:
            rerank_score_by_id = {}
            final_order = pre_rerank

        results: list[RetrievedPiece] = []
        for pid in final_order[:top_k]:
            unit = self._units_by_piece_id[pid]
            results.append(
                RetrievedPiece(
                    piece_id=pid,
                    clause_id=unit.clause_id,
                    text=unit.text,
                    fused_score=fused_scores.get(pid, 0.0),
                    rerank_score=rerank_score_by_id.get(pid),
                    unit=unit,
                )
            )
        _log.info(
            "hybrid retrieve: %d candidates -> %d after filters/dedup -> %d returned",
            len(fused_order), len(deduped_order), len(results),
        )
        return results

