from __future__ import annotations

import datetime as dt
from pathlib import Path

from eval.retrieval_harness import (
    DELIBERATE_ABSENCE,
    load_expected_clauses,
    load_probe_queries,
    run_retrieval_harness,
)
from ingestion.embedder import MockEmbedder
from ingestion.index_units import build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.bm25_index import build_bm25_index
from retrieval.hybrid_search import HybridRetriever
from retrieval.vector_index import VectorIndex

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def test_probe_queries_parses_all_43_probes_with_nonempty_text():
    probes = load_probe_queries()
    assert len(probes) == 43
    assert all(q.strip() for q in probes.values())
    # spot-check a narrative-format and a table-format probe
    assert probes["P-01"].startswith("I joined 1 Jan 2014")
    assert probes["P-40"] == "What is the notice period during probation in the UAE?"


def test_expected_clauses_map_has_an_entry_for_every_probe():
    probes = load_probe_queries()
    expected = load_expected_clauses()
    assert set(probes) <= set(expected)


def _build_retriever():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    bm25 = build_bm25_index(units)
    vector = VectorIndex(MockEmbedder(dimension=16))
    vector.build(units)
    return HybridRetriever(bm25, vector, units)


def test_harness_excludes_probes_with_no_scorable_expected_set():
    retriever = _build_retriever()
    report = run_retrieval_harness(retriever, top_k=5)
    # P-21/P-26/P-29/P-41 have an empty fixture list; P-39 is DELIBERATE_ABSENCE
    for pid in ("P-21", "P-26", "P-29", "P-39", "P-41"):
        assert pid in report.excluded_probe_ids
    assert report.scored_probe_count == 43 - len(report.excluded_probe_ids)
    assert report.scored_probe_count + len(report.excluded_probe_ids) == 43


def test_precision_and_recall_are_bounded_and_reported_per_probe():
    retriever = _build_retriever()
    report = run_retrieval_harness(retriever, top_k=5)
    assert 0.0 <= report.mean_precision <= 1.0
    assert 0.0 <= report.mean_recall <= 1.0
    assert len(report.per_probe) == report.scored_probe_count
    for r in report.per_probe:
        assert 0.0 <= r.precision <= 1.0
        assert 0.0 <= r.recall <= 1.0


def test_score_one_math_on_a_controlled_case():
    # deterministic unit-level check of the precision/recall formula itself,
    # independent of the real corpus/retriever (see run_retrieval_harness's
    # docstring for the exact definitions).
    from eval.retrieval_harness import _score_one

    expected = {"A", "B", "C"}
    retrieved = ["A", "X", "Y"]
    precision, recall = _score_one(expected, retrieved)
    assert precision == 1 / 3  # 1 hit ("A") out of 3 retrieved
    assert recall == 1 / 3  # 1 hit out of 3 expected


def test_perfect_retrieval_scores_precision_and_recall_of_one():
    from eval.retrieval_harness import _score_one

    expected = {"A", "B"}
    retrieved = ["A", "B"]
    precision, recall = _score_one(expected, retrieved)
    assert precision == 1.0
    assert recall == 1.0
