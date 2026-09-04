"""
M4's entry point: retrieve -> grade -> correct -> reason -> generate/clarify,
composed into one call. Everything this function calls (T-4.1-T-4.6) was
already unit-tested in isolation against real corpus fixtures; this module
exists to prove the COMPOSITION works -- that a query string goes in and a
correctly-shaped result comes out, with the corrective re-query and
temporal reasoning firing automatically, not just when a test hand-assembles
the exact pieces a stage needs.

Scope note, stated plainly rather than glossed over: `facts` (service
start date, valuation date) and `country`/`jurisdiction_scope` are NOT
extracted from the query text here -- parsing "I joined 1 Jan 2014 and
I'm resigning 30 Sep 2026... India" into structured facts is a natural-
language extraction step that was never a Phase 4 task (T-4.1-T-4.7 don't
include it), so this function takes them as arguments, already resolved,
the same way retrieve_and_grade already does for country/jurisdiction.
A caller (a future API layer, or an LLM-based fact extractor) supplies
them. This is not "M4 fully proven against the raw 43-probe text" --
that would need a fact-extraction component this phase doesn't build.
It IS the composed pipeline, correctly wired and demonstrated end-to-end
on the marquee real cases -- see tests/test_answer_pipeline.py.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from generation.generator import TemplateGenerator
from generation.schema import GeneratedAnswer
from grading.clarification import build_clarification, detect_missing_facts
from grading.pipeline import retrieve_and_grade
from grading.schema import ClarificationResponse, SufficiencyResult
from grading.temporal_reasoner import ServiceFacts, reason_over_pieces
from ingestion.logging_setup import get_logger
from retrieval.hybrid_search import DEFAULT_MIN_RERANK_SCORE, HybridRetriever
from retrieval.reranker import Reranker

_log = get_logger("grading.answer_pipeline")


@dataclass
class PipelineResult:
    status: str  # "ANSWERED" | "NEEDS_CLARIFICATION" | "INSUFFICIENT"
    answer: GeneratedAnswer | None = None
    clarification: ClarificationResponse | None = None
    sufficiency: SufficiencyResult | None = None
    pieces: list = None  # list[RetrievedPiece] actually retrieved -- added for Phase 5 eval
    """The retrieved pieces behind this result, whatever the status. Not used by
    answer_query's own control flow (that's graded.pieces internally); exposed
    so Phase 5's eval harness can build RAGAS "contexts" without re-retrieving.
    Untyped as list (not list[RetrievedPiece]) to avoid a retrieval.hybrid_search
    import here purely for a type hint -- grading/answer_pipeline.py otherwise
    has no reason to import RetrievedPiece."""
    faithfulness_score: float | None = None
    """Set only when grading.faithfulness_gate.apply_faithfulness_gate() has
    been run over this result (T-6.6) -- None means "gate not applied,"
    never "answer is unfaithful." Kept here rather than only in the gate's
    own return value so a refused result still carries the score that
    caused the refusal, for logging/demo/audit purposes."""
    refused_by_faithfulness_gate: bool = False
    """True iff this result started as ANSWERED and was converted to
    INSUFFICIENT by the live faithfulness gate (T-6.6) -- distinguishes a
    live faithfulness refusal from every other INSUFFICIENT cause (no
    relevant clause, missing lineage segment, etc.), which matters for
    T-6.8's re-run and for the demo narrative."""


def answer_query(
    retriever: HybridRetriever,
    query: str,
    country: str | None = None,
    jurisdiction_scope: str | None = None,
    as_of_date: dt.date | None = None,
    facts: ServiceFacts | None = None,
    reranker: Reranker | None = None,
    generator: TemplateGenerator | None = None,
    top_k: int = 10,
    min_rerank_score: float | None = DEFAULT_MIN_RERANK_SCORE,
) -> PipelineResult:
    """min_rerank_score defaults to the Session 6 calibrated floor (Phase 3
    reopened bug fix) -- pass None explicitly to get the old unfiltered
    behaviour."""
    facts = facts or ServiceFacts()
    generator = generator or TemplateGenerator()

    graded = retrieve_and_grade(
        retriever, query, top_k=top_k, country=country,
        jurisdiction_scope=jurisdiction_scope, as_of_date=as_of_date, reranker=reranker,
        min_rerank_score=min_rerank_score,
    )
    if not graded.sufficiency.is_sufficient:
        _log.info("answer_query: INSUFFICIENT even after correction (%s)", [r.value for r in graded.sufficiency.reasons])
        return PipelineResult(status="INSUFFICIENT", sufficiency=graded.sufficiency, pieces=graded.pieces)

    workings = reason_over_pieces(graded.pieces, facts)
    missing = detect_missing_facts(graded.pieces, workings, query_country=country)

    if missing:
        clarification = build_clarification(query, graded.pieces, workings, missing, generator)
        _log.info("answer_query: NEEDS_CLARIFICATION (%s)", [m.fact for m in missing])
        return PipelineResult(status="NEEDS_CLARIFICATION", clarification=clarification, sufficiency=graded.sufficiency, pieces=graded.pieces)

    answer = generator.generate(query, graded.pieces, workings)
    return PipelineResult(status="ANSWERED", answer=answer, sufficiency=graded.sufficiency, pieces=graded.pieces)
