"""T-8.4 tests: api/main.py, added retroactively in Session 10 after a
real bug was found by manual UI testing, not caught here first --
exactly the gap this file exists to close. The bug: _to_response()'s
NEEDS_CLARIFICATION branch sent only ca.condition ("if country = India")
to the UI and silently dropped ca.answer.text (the actual computed
answer for that branch), because ConditionalAnswer.answer is a full
GeneratedAnswer object and the first version of this function never
read its .text field. Retrieval/grading/generation were never at fault
-- this was a translation bug in brand-new glue code that had never
been exercised by a real request before a human clicked through it.

Same MockEmbedder/MockReranker convention as every other integration
test in this repo (test_answer_pipeline.py, test_hybrid_search.py,
test_clarification.py) -- real corpus fixtures, zero OpenAI/network
calls, so this suite costs nothing and never depends on external
services being reachable. Uses FastAPI's TestClient (starlette/httpx
under the hood) to exercise the real /query route, not just call
_to_response() as a bare function -- that way a request-shape or
routing regression would be caught here too, not just a translation bug."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

# api/main.py's module-level load_dotenv(".env") picks up LANGSMITH_TRACING=true
# from this project's real .env (needed for the live deployed app, not for tests).
# python-dotenv's load_dotenv() never overrides an already-set env var, so setting
# this to false BEFORE importing api.main makes every @traceable call in the real
# pipeline a documented no-op here (see grading/answer_pipeline.py's T-4.7 tracing
# tests for the same guarantee) instead of retrying a blocked network call on every
# traced function this suite exercises -- found for real: without this, running
# these tests took 10s alone but caused the FULL suite to exceed several minutes
# when run together, purely from LangSmith retry/flush overhead at interpreter exit.
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

import api.main as api_main
from fastapi.testclient import TestClient
from generation.generator import TemplateGenerator
from generation.schema import Citation, GeneratedAnswer
from grading.answer_pipeline import PipelineResult, answer_query
from grading.clarification import build_clarification, detect_missing_facts
from grading.schema import GradeVerdict, MissingReason, SufficiencyResult
from grading.temporal_reasoner import ServiceFacts
from ingestion.embedder import MockEmbedder
from ingestion.index_units import IndexableUnit, build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.bm25_index import build_bm25_index
from retrieval.hybrid_search import HybridRetriever, RetrievedPiece
from retrieval.reranker import MockReranker
from retrieval.vector_index import VectorIndex

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def _build_retriever() -> tuple[HybridRetriever, list[IndexableUnit]]:
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    bm25 = build_bm25_index(units)
    vector = VectorIndex(MockEmbedder(dimension=16))
    vector.build(units)
    return HybridRetriever(bm25, vector, units), units


# --- _to_response() unit tests: the exact function that had the bug ---


def test_to_response_answered_includes_citations_and_computed_amount():
    """Real end-to-end P-01 answer (real corpus, real generator, no
    network) -- ANSWERED must carry the answer text, every citation, and
    the computed rupee figure through to the JSON-shaped response."""
    retriever, _units = _build_retriever()
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30), monthly_wage=300000.0)
    result = answer_query(
        retriever, "gratuity ceiling maximum amount payable on termination",
        country="India", facts=facts, reranker=MockReranker(),
    )
    assert result.status == "ANSWERED"  # sanity: the pipeline itself did its job

    response = api_main._to_response(result)
    assert response.status == "ANSWERED"
    assert response.answer_text == result.answer.text
    assert {c.clause_id for c in response.citations} == {c.clause_id for c in result.answer.citations}
    assert response.computed_amount == 2_000_000.0  # the real capped ceiling figure


def test_to_response_needs_clarification_includes_real_answer_text_per_branch():
    """The exact regression this file exists to catch: each conditional
    answer's real text (not just its bare condition label) must survive
    the translation to JSON. Built the same way test_clarification.py's
    own proven country-ambiguity test does -- real corpus pieces, real
    build_clarification(), no mocking of the thing under test."""
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    india_notice = next(u for u in units if u.country == "India" and u.normative and u.doc_type == "policy")
    uae_notice = next(u for u in units if u.country == "UAE" and u.normative and u.doc_type == "policy")
    pieces = [
        RetrievedPiece(piece_id=india_notice.piece_id, clause_id=india_notice.clause_id, text=india_notice.text, fused_score=1.0, rerank_score=1.0, unit=india_notice),
        RetrievedPiece(piece_id=uae_notice.piece_id, clause_id=uae_notice.clause_id, text=uae_notice.text, fused_score=1.0, rerank_score=1.0, unit=uae_notice),
    ]
    missing = detect_missing_facts(pieces, [], query_country=None)
    clarification = build_clarification("how many days notice do I need to give", pieces, [], missing)
    assert len(clarification.conditional_answers) == 2  # sanity: real branches exist, each with real text

    result = PipelineResult(status="NEEDS_CLARIFICATION", clarification=clarification)
    response = api_main._to_response(result)

    assert response.status == "NEEDS_CLARIFICATION"
    assert len(response.conditional_answers) == 2
    for ca in response.conditional_answers:
        assert ca["condition"].startswith("if country = ")
        # THE bug: this used to be a KeyError / missing key entirely.
        assert ca["answer_text"], "conditional answer text was dropped in translation"
        assert ca["answer_text"] == next(
            real.answer.text for real in clarification.conditional_answers if real.condition == ca["condition"]
        )


def test_to_response_insufficient_includes_reasons():
    """Constructed directly (no retrieval needed) -- this is purely
    testing that _to_response reads SufficiencyResult.reasons correctly,
    not retrieval/grading behaviour (already covered in test_crag_grader.py)."""
    sufficiency = SufficiencyResult(verdict=GradeVerdict.INSUFFICIENT, reasons=[MissingReason.NO_RELEVANT_CLAUSE])
    result = PipelineResult(status="INSUFFICIENT", sufficiency=sufficiency)

    response = api_main._to_response(result)
    assert response.status == "INSUFFICIENT"
    assert response.insufficient_reasons == ["no_relevant_clause"]
    assert response.answer_text is None
    assert response.citations == []


# --- Real HTTP-shaped requests through the actual /query route ---


def _client_with_test_retriever() -> TestClient:
    """Wires api.main's module-level globals directly, bypassing the
    real @app.on_event("startup") handler (which needs a real
    OPENAI_API_KEY and would try to build a real OpenAIEmbedder) --
    same substitution principle as every other test in this repo:
    replace the network-dependent piece, keep everything else real."""
    retriever, _units = _build_retriever()
    api_main._retriever = retriever
    api_main._reranker = MockReranker()
    return TestClient(api_main.app)


def test_health_endpoint():
    client = _client_with_test_retriever()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_query_endpoint_answered_real_request_shape():
    """A real HTTP POST, real JSON body, real JSON response -- this is
    what would have caught the missing-field bug even without hand-
    constructing a PipelineResult, since it exercises FastAPI's actual
    response-model serialization too."""
    client = _client_with_test_retriever()
    resp = client.post(
        "/query",
        json={
            "query": "gratuity ceiling maximum amount payable on termination",
            "country": "India",
            "service_start_date": "2014-01-01",
            "valuation_date": "2026-09-30",
            "monthly_wage": 300000.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ANSWERED"
    assert body["computed_amount"] == 2_000_000.0
    assert any(c["clause_id"] == "IN-GRAT-S4-CEILING" for c in body["citations"])


def test_query_endpoint_rejects_empty_query():
    """Pydantic's min_length=1 on QueryRequest.query should reject an
    empty string before answer_query() is ever called -- a 422, not a
    500 from deep inside the pipeline."""
    client = _client_with_test_retriever()
    resp = client.post("/query", json={"query": ""})
    assert resp.status_code == 422
