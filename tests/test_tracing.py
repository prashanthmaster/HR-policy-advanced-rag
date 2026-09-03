"""T-4.7: LangSmith tracing on retrieval/grading/generation.

`@traceable` (langsmith) wraps HybridRetriever.retrieve, grade_sufficiency,
retrieve_and_grade, reason_over_pieces, and TemplateGenerator.generate.
By design this must be a complete no-op with no network call whenever
tracing isn't explicitly enabled (no LANGCHAIN_TRACING_V2/LANGSMITH_TRACING
env var, no API key) -- same "pytest must never depend on an external
call succeeding" rule as ingestion/embedder.py and retrieval/reranker.py.
These tests prove the wrapped functions still behave correctly in that
default-off state; they deliberately do NOT enable real tracing (that
would introduce network dependence into the suite, and this sandbox's
proxy blocks LangSmith's API the same way it blocks api.openai.com and
huggingface.co -- see slot4_progress.md)."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pytest

from generation.generator import TemplateGenerator
from grading.crag_grader import grade_sufficiency
from grading.schema import GradeVerdict
from grading.temporal_reasoner import ServiceFacts, reason_over_pieces
from ingestion.embedder import MockEmbedder
from ingestion.index_units import IndexableUnit, build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.bm25_index import build_bm25_index
from retrieval.hybrid_search import HybridRetriever, RetrievedPiece
from retrieval.reranker import MockReranker
from retrieval.vector_index import VectorIndex

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def test_tracing_env_vars_are_not_set_in_ci():
    """Documents the invariant the rest of this file relies on: tracing
    is off by default, so @traceable degrades to a plain function call
    with zero network I/O."""
    assert os.environ.get("LANGCHAIN_TRACING_V2") != "true"
    assert os.environ.get("LANGSMITH_TRACING") != "true"


@pytest.fixture(scope="module")
def units() -> list[IndexableUnit]:
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    return build_indexable_units(chunks)


def _piece_for(units: list[IndexableUnit], clause_id: str) -> RetrievedPiece:
    unit = next(u for u in units if u.clause_id == clause_id)
    return RetrievedPiece(
        piece_id=unit.piece_id, clause_id=unit.clause_id, text=unit.text,
        fused_score=1.0, rerank_score=1.0, unit=unit,
    )


def test_traced_retrieve_still_works(units):
    bm25 = build_bm25_index(units)
    vector = VectorIndex(MockEmbedder(dimension=16))
    vector.build(units)
    retriever = HybridRetriever(bm25, vector, units)
    results = retriever.retrieve("gratuity ceiling", top_k=5, country="India", reranker=MockReranker())
    assert len(results) > 0


def test_traced_grade_sufficiency_still_works(units):
    piece = _piece_for(units, "IN-GRAT-S4-CEILING")
    result = grade_sufficiency([piece])
    assert result.verdict is GradeVerdict.SUFFICIENT


def test_traced_reason_over_pieces_still_works(units):
    piece = _piece_for(units, "IN-GRAT-S4-CEILING")
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30))
    workings = reason_over_pieces([piece], facts)
    assert len(workings) == 1


def test_traced_generate_still_works(units):
    piece = _piece_for(units, "IN-GRAT-S4-CEILING")
    answer = TemplateGenerator().generate("what gratuity do I get", [piece], [])
    assert answer.text
    assert len(answer.citations) == 1
