"""T-6.6 tests: the live faithfulness refusal gate. Uses a fake, deterministic
scorer throughout -- NEVER grading.ragas_client.score_faithfulness -- so
this test file can never make a real OpenAI call or spend money."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from grading.answer_pipeline import answer_query
from grading.faithfulness_gate import apply_faithfulness_gate
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


def _answered_result():
    retriever = _build_retriever()
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30))
    query = "gratuity ceiling maximum amount payable on termination -- joined 1 Jan 2014, resigning 30 Sep 2026"
    result = answer_query(
        retriever, query, country="India", facts=facts, reranker=MockReranker(),
    )
    assert result.status == "ANSWERED"  # sanity: fixture assumption
    return query, result


def test_gate_is_noop_when_threshold_is_none():
    query, result = _answered_result()
    scorer_called = []

    def scorer(q, a, c):
        scorer_called.append((q, a, c))
        return 0.0  # would fail any real threshold -- must never even be consulted

    gated = apply_faithfulness_gate(result, query, scorer, threshold=None)
    assert gated is result  # unchanged, same object
    assert scorer_called == []  # scorer never called at all when ungated


def test_gate_passes_through_when_score_at_or_above_threshold():
    query, result = _answered_result()
    gated = apply_faithfulness_gate(result, query, lambda q, a, c: 0.9, threshold=0.5)
    assert gated.status == "ANSWERED"
    assert gated.faithfulness_score == 0.9
    assert gated.refused_by_faithfulness_gate is False
    assert gated.answer is result.answer  # answer content untouched


def test_gate_refuses_when_score_below_threshold():
    query, result = _answered_result()
    gated = apply_faithfulness_gate(result, query, lambda q, a, c: 0.1, threshold=0.5)
    assert gated.status == "INSUFFICIENT"
    assert gated.faithfulness_score == 0.1
    assert gated.refused_by_faithfulness_gate is True


def test_gate_does_not_mutate_the_original_result():
    query, result = _answered_result()
    apply_faithfulness_gate(result, query, lambda q, a, c: 0.1, threshold=0.5)
    assert result.status == "ANSWERED"  # original untouched
    assert result.faithfulness_score is None
    assert result.refused_by_faithfulness_gate is False


def test_gate_is_noop_for_non_answered_statuses():
    # A NEEDS_CLARIFICATION/INSUFFICIENT result has no answer to check
    # faithfulness against -- the gate must never touch it.
    from grading.answer_pipeline import PipelineResult
    non_answered = PipelineResult(status="NEEDS_CLARIFICATION")
    gated = apply_faithfulness_gate(non_answered, "any query", lambda q, a, c: 0.0, threshold=0.5)
    assert gated is non_answered


def test_gate_passes_actual_answer_text_and_contexts_to_scorer():
    query, result = _answered_result()
    captured = {}

    def scorer(q, a, c):
        captured["question"] = q
        captured["answer"] = a
        captured["contexts"] = c
        return 1.0

    apply_faithfulness_gate(result, query, scorer, threshold=0.5)
    assert captured["question"] == query
    assert captured["answer"] == result.answer.text
    assert captured["contexts"] == [p.text for p in result.pieces]
