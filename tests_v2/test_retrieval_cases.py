from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from hr_policy_rag.corpus import CorpusUse, load_verified_corpus
from hr_policy_rag.evaluation import RetrievalSplit, load_retrieval_case_set

ROOT = Path(__file__).resolve().parents[1]
CASE_SET_PATH = ROOT / "evaluation" / "v2" / "retrieval_cases.json"
CORPUS_MANIFEST_PATH = ROOT / "corpus_v2" / "manifest.json"


def test_retrieval_exam_is_frozen_balanced_and_bound_to_this_corpus() -> None:
    case_set = load_retrieval_case_set(CASE_SET_PATH)
    corpus = load_verified_corpus(CORPUS_MANIFEST_PATH, repository_root=ROOT)

    assert case_set.corpus_generation == corpus.manifest.corpus_generation
    assert len(case_set.cases) == 36
    assert Counter(case.split for case in case_set.cases) == {
        RetrievalSplit.DEVELOPMENT: 12,
        RetrievalSplit.REGRESSION: 12,
        RetrievalSplit.HOLDOUT: 12,
    }
    assert Counter((case.split, case.jurisdiction, case.topic) for case in case_set.cases) == {
        (split, jurisdiction, topic): 2
        for split in RetrievalSplit
        for jurisdiction in ("India", "UAE")
        for topic in ("gratuity", "notice", "leave")
    }


def test_all_targets_exist_in_serving_corpus_and_match_case_metadata() -> None:
    case_set = load_retrieval_case_set(CASE_SET_PATH)
    corpus = load_verified_corpus(CORPUS_MANIFEST_PATH, repository_root=ROOT)
    sources = {source.source_id: source for source in corpus.manifest.sources}

    for case in case_set.cases:
        target_ids = {source_id for group in case.required_source_groups for source_id in group}
        for source_id in target_ids:
            source = sources[source_id]
            assert source.use is CorpusUse.SERVING
            assert source.jurisdiction in {case.jurisdiction, "GLOBAL"}
            assert case.topic in source.topics
            assert source.effective_from is not None
            assert source.effective_from <= case.as_of_date
            assert source.effective_to is None or case.as_of_date < source.effective_to


def test_temporal_cases_forbid_the_opposite_policy_version() -> None:
    case_set = load_retrieval_case_set(CASE_SET_PATH)
    temporal_cases = [case for case in case_set.cases if case.forbidden_source_ids]

    assert len(temporal_cases) >= 24
    assert all(case.forbidden_source_ids for case in temporal_cases)


def test_quality_thresholds_are_frozen_before_retrieval_implementation() -> None:
    thresholds = load_retrieval_case_set(CASE_SET_PATH).thresholds

    assert thresholds.recall_at_10 == 0.9
    assert thresholds.minimum_slice_recall_at_10 == 0.85
    assert thresholds.reciprocal_rank_at_10 == 0.75
    assert thresholds.temporal_accuracy == 1.0
    assert thresholds.maximum_filter_leakage == 0
    assert thresholds.maximum_errors == 0
    assert thresholds.maximum_exclusions == 0


def test_modified_case_content_is_rejected_even_when_schema_is_valid(tmp_path: Path) -> None:
    raw = json.loads(CASE_SET_PATH.read_text(encoding="utf-8"))
    raw["cases"][0]["query"] += " changed"
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="digest mismatch"):
        load_retrieval_case_set(changed)


@pytest.mark.parametrize("raw", [{}, {"cases": {}}, []])
def test_malformed_case_sets_fail_closed(tmp_path: Path, raw: object) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="cases array"):
        load_retrieval_case_set(path)
