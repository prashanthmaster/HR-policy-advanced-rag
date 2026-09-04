"""M4 end-to-end proof: a query string goes into answer_query() and a
correctly-shaped result comes out, with T-4.2's correction and T-4.3's
temporal reasoning firing automatically -- not hand-assembled by the
test. Same MockEmbedder/MockReranker convention as
tests/test_hybrid_search.py: proves the WIRING, not semantic retrieval
quality (that's T-3.6's job, against real embeddings)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from grading.answer_pipeline import answer_query
from grading.temporal_reasoner import ServiceFacts
from ingestion.embedder import MockEmbedder
from ingestion.index_units import build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.bm25_index import build_bm25_index
from retrieval.hybrid_search import HybridRetriever
from retrieval.reranker import MockReranker
from retrieval.vector_index import VectorIndex

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def _build_retriever():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    bm25 = build_bm25_index(units)
    vector = VectorIndex(MockEmbedder(dimension=16))
    vector.build(units)
    return HybridRetriever(bm25, vector, units)


def test_p01_end_to_end_answers_without_splitting():
    """India gratuity ceiling, straight from query text to a generated
    answer -- must not split, must cite IN-GRAT-S4-CEILING."""
    retriever = _build_retriever()
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30))
    result = answer_query(
        retriever,
        "gratuity ceiling maximum amount payable on termination -- joined 1 Jan 2014, resigning 30 Sep 2026",
        country="India",
        facts=facts,
        reranker=MockReranker(),
    )
    assert result.status == "ANSWERED"
    assert "does not get split" in result.answer.text
    assert any(c.clause_id == "IN-GRAT-S4-CEILING" for c in result.answer.citations)


def test_p3a_end_to_end_self_corrects_and_splits():
    """DIFC DEWS straddle: retrieval alone would normally surface only
    the current (post-2020) segment -- the corrective re-query (T-4.2)
    must pull in the legacy segment automatically, and the answer must
    show both segments split at 2020-02-01, with both cited. Nothing
    here is hand-assembled -- it starts from a query string."""
    retriever = _build_retriever()
    facts = ServiceFacts(service_start_date=dt.date(2017, 1, 1), valuation_date=dt.date(2026, 9, 3))
    result = answer_query(
        retriever,
        "I've been with the DIFC entity since 2017 and I'm leaving this year. What's my end of service?",
        country="UAE",
        jurisdiction_scope="uae-difc",
        facts=facts,
        reranker=MockReranker(),
    )
    assert result.status == "ANSWERED"
    assert "2020-02-01" in result.answer.text
    cited_ids = {c.clause_id for c in result.answer.citations}
    assert "DIFC-L2-2019-DEWS" in cited_ids
    assert "DIFC-EOSB-LEGACY-GRATUITY" in cited_ids


def test_p06_end_to_end_needs_clarification_not_a_guess():
    """The grandfathered supplement, with no joining date supplied --
    must return NEEDS_CLARIFICATION, not a confident answer either way."""
    retriever = _build_retriever()
    result = answer_query(
        retriever,
        "My colleague in Dubai gets an end-of-service supplement on top of gratuity. HR says I don't get it. Who's right?",
        country="UAE",
        jurisdiction_scope="uae-mainland",
        reranker=MockReranker(),
    )
    assert result.status == "NEEDS_CLARIFICATION"
    assert any(mf.fact == "service_start_date" for mf in result.clarification.missing_facts)
    assert result.answer is None


def test_p01_result_exposes_retrieved_pieces_for_eval():
    """Phase 5's eval harness needs the retrieved pieces (for RAGAS
    "contexts") without re-retrieving -- PipelineResult.pieces exposes
    exactly what generation/clarification/insufficiency was based on."""
    retriever = _build_retriever()
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30))
    result = answer_query(
        retriever,
        "gratuity ceiling maximum amount payable on termination -- joined 1 Jan 2014, resigning 30 Sep 2026",
        country="India",
        facts=facts,
        reranker=MockReranker(),
    )
    assert result.pieces is not None
    assert len(result.pieces) > 0
    assert any(p.clause_id == "IN-GRAT-S4-CEILING" for p in result.pieces)


def test_answer_query_defaults_to_the_calibrated_min_rerank_score_floor():
    """Same wiring check as grading/pipeline.py's, one layer up: answer_query()
    is the real M4 entry point everything (including the eval scripts) calls,
    so this is what actually has to default to the Session 6 fix."""
    import inspect
    from retrieval.hybrid_search import DEFAULT_MIN_RERANK_SCORE

    sig = inspect.signature(answer_query)
    assert sig.parameters["min_rerank_score"].default == DEFAULT_MIN_RERANK_SCORE
