"""
T-4.2: bounded corrective re-query, driven by T-4.1's sufficiency grading.

CRAG's original paper corrects insufficient context with a web search.
That's explicitly out of scope here (no live employee DB / external
lookups -- see slot4_design.md's scope decisions), so "corrective"
means something narrower and fully within this project's own index:

  - MISSING_SEGMENT_VERSIONS (Finding 1): the missing piece was never
    absent from the index -- select_current_as_of (T-3.3) deliberately
    filtered it out because it decides which ONE version is "current" as
    of a date, and a SEGMENTED_ACCRUAL/ELECTIVE clause needs more than
    one. The correction is a direct lookup (HybridRetriever.lineage_versions),
    not a new search.
  - NO_RELEVANT_CLAUSE: nothing on-topic came back at all. The
    correction here is a genuine retry -- widen the candidate pool
    (larger top_k / rerank_candidate_k) once, in case the original
    top_k truncated past something relevant rather than the corpus
    simply not having it.
  - MISSING_EFFECTIVE_DATE / MISSING_COHORT_RULE: these are corpus
    metadata gaps (R-09's deliberate unresolved date; a GRANDFATHERED
    clause retrieved without its own cohort_rule field, which would be
    an ingestion bug, not a retrieval one). No re-query fixes a fact the
    index doesn't have -- correction does not attempt one, and the
    result stays INSUFFICIENT for T-4.4/T-4.5 to act on (decline, or
    ask a clarifying question, per Finding 5) rather than silently
    guessing.

Bounded to exactly one corrective pass, per T-4.2's spec -- an
unbounded retry loop against a fixed corpus can only ever converge or
spin; one pass is enough to fix both correctable cases above (the
lineage lookup is exhaustive on the first try; the widened top_k either
finds something or the corpus doesn't have it).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from langsmith import traceable

from grading.crag_grader import grade_sufficiency
from grading.schema import GradeVerdict, MissingReason, SufficiencyResult
from ingestion.logging_setup import get_logger
from retrieval.hybrid_search import DEFAULT_MIN_RERANK_SCORE, HybridRetriever, RetrievedPiece
from retrieval.reranker import Reranker

_log = get_logger("grading.pipeline")

# How much wider the corrective retry casts its net when nothing
# relevant came back the first time. Same status as rrf_k=60 elsewhere
# in this project: a documented default, not a measured/calibrated one.
_WIDENED_TOP_K_MULTIPLIER = 2


@dataclass
class GradedRetrieval:
    pieces: list[RetrievedPiece]
    sufficiency: SufficiencyResult
    corrected: bool
    """True iff the corrective re-query path fired at all (whether or
    not it actually resolved sufficiency)."""


@traceable(name="retrieve_and_grade", run_type="chain")
def retrieve_and_grade(
    retriever: HybridRetriever,
    query: str,
    top_k: int = 10,
    country: str | None = None,
    jurisdiction_scope: str | None = None,
    as_of_date: dt.date | None = None,
    reranker: Reranker | None = None,
    min_rerank_score: float | None = DEFAULT_MIN_RERANK_SCORE,
) -> GradedRetrieval:
    """min_rerank_score defaults to the Session 6 calibrated floor (Phase 3
    reopened bug fix) -- pass None explicitly to get the old unfiltered
    behaviour, e.g. for a test that wants to see the full padded-out set."""
    pieces = retriever.retrieve(
        query,
        top_k=top_k,
        country=country,
        jurisdiction_scope=jurisdiction_scope,
        as_of_date=as_of_date,
        reranker=reranker,
        min_rerank_score=min_rerank_score,
    )
    result = grade_sufficiency(pieces)
    if result.is_sufficient:
        return GradedRetrieval(pieces=pieces, sufficiency=result, corrected=False)

    corrected_pieces = pieces
    attempted_correction = False

    if MissingReason.MISSING_SEGMENT_VERSIONS in result.reasons:
        attempted_correction = True
        existing_ids = {p.piece_id for p in corrected_pieces}
        existing_clause_ids = {p.clause_id for p in corrected_pieces}
        lineages_needing_versions = {
            p.unit.lineage_id
            for p in pieces
            if p.unit.normative and p.unit.lineage_id and p.unit.temporal_applicability in ("SEGMENTED_ACCRUAL", "ELECTIVE")
        }
        added = 0
        for lineage_id in lineages_needing_versions:
            for unit in retriever.lineage_versions(lineage_id):
                if unit.piece_id in existing_ids or unit.clause_id in existing_clause_ids:
                    continue
                corrected_pieces = corrected_pieces + [
                    RetrievedPiece(
                        piece_id=unit.piece_id,
                        clause_id=unit.clause_id,
                        text=unit.text,
                        fused_score=0.0,
                        rerank_score=None,
                        unit=unit,
                    )
                ]
                existing_ids.add(unit.piece_id)
                existing_clause_ids.add(unit.clause_id)
                added += 1
        _log.info("corrective re-query: added %d lineage-sibling piece(s) for %s", added, lineages_needing_versions)

    if MissingReason.NO_RELEVANT_CLAUSE in result.reasons:
        attempted_correction = True
        widened = retriever.retrieve(
            query,
            top_k=top_k * _WIDENED_TOP_K_MULTIPLIER,
            country=country,
            jurisdiction_scope=jurisdiction_scope,
            as_of_date=as_of_date,
            reranker=reranker,
            min_rerank_score=min_rerank_score,
        )
        _log.info("corrective re-query: widened top_k %d -> %d, %d pieces returned", top_k, top_k * _WIDENED_TOP_K_MULTIPLIER, len(widened))
        corrected_pieces = widened

    if not attempted_correction:
        return GradedRetrieval(pieces=pieces, sufficiency=result, corrected=False)

    final_result = grade_sufficiency(corrected_pieces)
    return GradedRetrieval(pieces=corrected_pieces, sufficiency=final_result, corrected=True)
