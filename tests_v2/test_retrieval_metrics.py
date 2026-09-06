from __future__ import annotations

from pathlib import Path

from hr_policy_rag.corpus import load_verified_corpus
from hr_policy_rag.domain import Evidence
from hr_policy_rag.evaluation import (
    RetrievalCaseScore,
    aggregate_scores,
    load_retrieval_case_set,
    passes_thresholds,
    score_case,
)

ROOT = Path(__file__).resolve().parents[1]
CASE_SET_PATH = ROOT / "evaluation" / "v2" / "retrieval_cases.json"
CORPUS_MANIFEST_PATH = ROOT / "corpus_v2" / "manifest.json"


def _evidence(source_id: str, index: int = 0) -> Evidence:
    return Evidence(
        evidence_id=f"e-{index}",
        chunk_id=f"c-{index}",
        source_id=source_id,
        corpus_generation="generation",
        quote="Policy evidence.",
        locator="section 1",
        retrieval_score=0.5,
    )


def test_case_scoring_uses_source_groups_rank_and_filter_integrity() -> None:
    case = load_retrieval_case_set(CASE_SET_PATH).cases[0]
    corpus = load_verified_corpus(CORPUS_MANIFEST_PATH, repository_root=ROOT)
    sources = {source.source_id: source for source in corpus.manifest.sources}
    score = score_case(
        case,
        [_evidence("meridian-global-answering-guide-v1"), _evidence("in-coss-2020-raw", 1)],
        sources,
    )

    assert score.target_recall == 1
    assert score.reciprocal_rank == 0.5
    assert score.temporal_correct
    assert score.filter_leakage_count == 0


def test_case_scoring_detects_forbidden_versions_and_wrong_scope() -> None:
    case = load_retrieval_case_set(CASE_SET_PATH).cases[0]
    corpus = load_verified_corpus(CORPUS_MANIFEST_PATH, repository_root=ROOT)
    sources = {source.source_id: source for source in corpus.manifest.sources}
    score = score_case(
        case,
        [_evidence("meridian-india-gratuity-policy-2023"), _evidence("meridian-uae-eos-policy-2025", 1)],
        sources,
        error_code="RETRIEVAL_UNAVAILABLE",
    )

    assert score.target_recall == 0
    assert score.reciprocal_rank == 0
    assert not score.temporal_correct
    assert score.filter_leakage_count == 2
    assert score.error_code == "RETRIEVAL_UNAVAILABLE"


def test_aggregate_and_frozen_threshold_gate() -> None:
    passing = RetrievalCaseScore(
        case_id="pass",
        returned_source_ids=("source",),
        target_recall=1,
        reciprocal_rank=1,
        temporal_correct=True,
        filter_leakage_count=0,
    )
    aggregate = aggregate_scores([passing])
    thresholds = load_retrieval_case_set(CASE_SET_PATH).thresholds

    assert aggregate.recall_at_10 == 1
    assert passes_thresholds(aggregate, thresholds, [aggregate])

    failing = aggregate_scores([passing.model_copy(update={"target_recall": 0.5})])
    assert not passes_thresholds(failing, thresholds, [failing])


def test_empty_aggregate_fails_closed_and_zero_results_do_not_divide_by_zero() -> None:
    try:
        aggregate_scores([])
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("empty evaluation unexpectedly succeeded")

    empty_result = RetrievalCaseScore(
        case_id="empty",
        returned_source_ids=(),
        target_recall=0,
        reciprocal_rank=0,
        temporal_correct=True,
        filter_leakage_count=0,
    )
    assert aggregate_scores([empty_result]).filter_leakage == 0
