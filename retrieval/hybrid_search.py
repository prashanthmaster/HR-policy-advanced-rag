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
  7. Drop pieces below min_rerank_score (Session 5 fix, see below), THEN
     truncate to top_k.

Steps 3 and 4 filter a SET (order doesn't matter, they only decide
membership); the fused rank order from step 2 is what determines each
kept piece's position before rerank.

Reopened 2026-09-04 (Session 5) -- real bug, found downstream on Phase 5's
first live T-5.4 run, traced back here: step 7 used to be an unconditional
truncate to exactly top_k, with NO floor on relevance. Every query got
padded out to top_k candidates regardless of how low a low-ranked piece's
rerank_score actually was -- so a query about housing allowance still
returned 10 pieces including DIFC leave, notice, probation, gratuity-
ceiling clauses that had nothing to do with it. This was silently
compatible with everything downstream: grading/crag_grader.py's own
docstring already documents its assumption that "whether a clause is
topically ON-TOPIC for a free-text query... already happened at rerank"
-- that assumption was correct about WHERE the filtering should happen,
just wrong that it actually did. grading/temporal_reasoner.py then wraps
every retrieved normative piece with a temporal_applicability tag into
its own trivial TemporalWorking (by design, for pieces with no amendment
pair/alternative to reason over), so the padded-out irrelevant pieces
each became their own "governing_piece" and generation/generator.py's
citation-narrowing fix (48daa40) narrowed nothing in practice.

min_rerank_score (new parameter, default None = OLD behaviour unchanged)
is the fix: once a reranker has scored the candidate pool, drop anything
scoring below the floor BEFORE truncating to top_k, so top_k becomes a
ceiling rather than a fixed target. Deliberately does NOT apply to the
fused_score (RRF-based) fallback path when no reranker is supplied --
fused_score is a reciprocal-RANK score, not a calibrated relevance
magnitude, so a floor on it would need its own separate calibration
work and isn't attempted here; that path stays explicitly unfloored and
documented as such, not silently assumed equivalent.

The actual floor VALUE is not set as a new default here on purpose --
this project's standing rule is no constant without calibration against
real data (same status rrf_k=60 and rerank_candidate_k=20 already have).
scripts/dump_rerank_scores.py is the calibration script: it prints real
FlashRankReranker score distributions for a few representative queries
(a genuinely single-topic one like P-30's housing-allowance query, and
genuinely multi-clause ones like P-02/P-3a that legitimately need 2+
pieces) so the floor can be picked from real numbers, not guessed, and
so it doesn't accidentally cut a legitimate segmented-accrual pair.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from langsmith import traceable

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

    def lineage_versions(self, lineage_id: str) -> list[IndexableUnit]:
        """T-4.2: every indexed unit sharing a lineage_id, bypassing
        select_current_as_of's single-version-per-lineage collapse. The
        corrective re-query path uses this to pull in a SEGMENTED_ACCRUAL
        clause's other segment(s) once grading (T-4.1) has flagged that
        the as-of-resolved retrieval only surfaced one of them -- it is
        not a fresh search, just a direct lookup against what is already
        indexed, since the missing piece was never absent from the
        index, only filtered out of THIS query's result by design."""
        return [u for u in self._units_by_piece_id.values() if u.lineage_id == lineage_id]

    @traceable(name="hybrid_retrieve", run_type="retriever")
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
        min_rerank_score: float | None = None,
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
            if min_rerank_score is not None:
                before = len(final_order)
                final_order = [pid for pid in final_order if rerank_score_by_id[pid] >= min_rerank_score]
                _log.info(
                    "min_rerank_score=%.4f dropped %d/%d reranked candidate(s)",
                    min_rerank_score, before - len(final_order), before,
                )
        else:
            rerank_score_by_id = {}
            final_order = pre_rerank
            if min_rerank_score is not None:
                # Documented scope limit, not an oversight: fused_score is a
                # reciprocal-RANK score (fusion.py), not a calibrated relevance
                # magnitude the way a cross-encoder's rerank_score is -- a
                # floor on it needs its own separate calibration and isn't
                # attempted here. See this module's docstring.
                _log.warning(
                    "min_rerank_score=%.4f requested but no reranker ran -- ignored "
                    "(fused_score is not a relevance-floored signal; see module docstring)",
                    min_rerank_score,
                )

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

