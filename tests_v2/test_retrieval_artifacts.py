from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from hr_policy_rag.corpus import ManifestSource, load_verified_corpus
from hr_policy_rag.evaluation import (
    RetrievalAggregate,
    RetrievalCase,
    RetrievalCaseScore,
    RetrievalEvaluationMode,
    RetrievalEvaluationReport,
    RetrievalSplit,
    aggregate_scores,
    load_retrieval_case_set,
    passes_thresholds,
)

ROOT = Path(__file__).resolve().parents[1]
CASE_SET_PATH = ROOT / "evaluation" / "v2" / "retrieval_cases.json"
CORPUS_MANIFEST_PATH = ROOT / "corpus_v2" / "manifest.json"
DEVELOPMENT_RESULT = ROOT / "artifacts" / "v2" / "retrieval" / "development-59cb2ef.json"
RELEASE_RESULT = ROOT / "artifacts" / "v2" / "retrieval" / "release-01d93a8.json"
JsonObject = dict[str, Any]


def _source_leaks(case: RetrievalCase, source: ManifestSource | None) -> bool:
    if source is None or source.effective_from is None:
        return True
    return (
        source.jurisdiction not in {case.jurisdiction, "GLOBAL"}
        or case.topic not in source.topics
        or source.effective_from > case.as_of_date
        or (source.effective_to is not None and case.as_of_date >= source.effective_to)
    )


def _recompute_row(
    case: RetrievalCase,
    recorded: RetrievalCaseScore,
    sources: dict[str, ManifestSource],
) -> RetrievalCaseScore:
    source_ids = recorded.returned_source_ids[:10]
    targets = {source_id for group in case.required_source_groups for source_id in group}
    hit_groups = sum(any(source_id in source_ids for source_id in group) for group in case.required_source_groups)
    first_rank = next((rank for rank, source_id in enumerate(source_ids, start=1) if source_id in targets), None)
    leakage = sum(_source_leaks(case, sources.get(source_id)) for source_id in source_ids)
    return RetrievalCaseScore(
        case_id=case.case_id,
        returned_source_ids=source_ids,
        target_recall=hit_groups / len(case.required_source_groups),
        reciprocal_rank=0 if first_rank is None else 1 / first_rank,
        temporal_correct=not bool(set(source_ids) & set(case.forbidden_source_ids)),
        filter_leakage_count=leakage,
        error_code=recorded.error_code,
    )


def _load_and_recompute(path: Path) -> tuple[RetrievalEvaluationReport, dict[str, RetrievalAggregate]]:
    report = RetrievalEvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))
    case_set = load_retrieval_case_set(CASE_SET_PATH)
    corpus = load_verified_corpus(CORPUS_MANIFEST_PATH, repository_root=ROOT)
    cases = {case.case_id: case for case in case_set.cases}
    sources = {source.source_id: source for source in corpus.manifest.sources}

    recomputed = tuple(_recompute_row(cases[row.case_id], row, sources) for row in report.cases)
    assert recomputed == report.cases
    assert aggregate_scores(recomputed) == report.aggregate

    grouped: defaultdict[tuple[str, str], list[RetrievalCaseScore]] = defaultdict(list)
    for row in recomputed:
        case = cases[row.case_id]
        grouped[(case.jurisdiction, case.topic)].append(row)
    slices = {
        f"{jurisdiction}:{topic}": aggregate_scores(rows) for (jurisdiction, topic), rows in sorted(grouped.items())
    }
    assert slices == report.slices
    assert report.case_set_sha256 == case_set.cases_sha256
    assert {cases[row.case_id].split for row in report.cases} == set(report.included_splits)
    assert report.passed == passes_thresholds(report.aggregate, report.thresholds, tuple(slices.values()))
    return report, slices


def test_checked_in_development_artifact_is_self_consistent() -> None:
    report, slices = _load_and_recompute(DEVELOPMENT_RESULT)

    assert report.mode is RetrievalEvaluationMode.DEVELOPMENT
    assert report.included_splits == (RetrievalSplit.DEVELOPMENT, RetrievalSplit.REGRESSION)
    assert report.aggregate.case_count == 24
    assert report.aggregate.recall_at_10 == 1
    assert math.isclose(report.aggregate.reciprocal_rank_at_10, 0.9434523809523809)
    assert min(item.recall_at_10 for item in slices.values()) == 1


def test_checked_in_release_artifact_and_unseen_holdout_pass_frozen_gates() -> None:
    report, _ = _load_and_recompute(RELEASE_RESULT)
    case_set = load_retrieval_case_set(CASE_SET_PATH)
    cases = {case.case_id: case for case in case_set.cases}
    holdout = tuple(row for row in report.cases if cases[row.case_id].split is RetrievalSplit.HOLDOUT)
    holdout_aggregate = aggregate_scores(holdout)

    assert report.mode is RetrievalEvaluationMode.RELEASE
    assert set(report.included_splits) == set(RetrievalSplit)
    assert report.aggregate.case_count == 36
    assert report.aggregate.recall_at_10 == 1
    assert math.isclose(report.aggregate.reciprocal_rank_at_10, 0.9484126984126985)
    assert holdout_aggregate.case_count == 12
    assert holdout_aggregate.recall_at_10 == 1
    assert math.isclose(holdout_aggregate.reciprocal_rank_at_10, 0.9583333333333334)
    assert holdout_aggregate.temporal_accuracy == 1
    assert holdout_aggregate.filter_leakage == 0
    assert holdout_aggregate.errors == 0
    assert hashlib.sha256(RELEASE_RESULT.read_bytes()).hexdigest() == (
        "59e9c43c0edcb2e5c8498df48acc57457b3bd6b96ae66d808e08a62e7cd116b1"
    )


def _duplicate_split(data: JsonObject) -> None:
    splits = data["included_splits"]
    assert isinstance(splits, list)
    cast(list[object], splits).append("DEVELOPMENT")


def _append_case(data: JsonObject) -> None:
    cases = data["cases"]
    assert isinstance(cases, list)
    case_list = cast(list[object], cases)
    case_list.append(case_list[0])


def _duplicate_case_id(data: JsonObject) -> None:
    cases = data["cases"]
    assert isinstance(cases, list)
    cases[1] = cases[0]


def _invert_pass(data: JsonObject) -> None:
    data["passed"] = False


def test_evaluation_report_rejects_internally_contradictory_evidence() -> None:
    mutations: tuple[tuple[Callable[[JsonObject], None], str], ...] = (
        (_duplicate_split, "splits must be unique"),
        (_append_case, "case count does not match"),
        (_duplicate_case_id, "case IDs must be unique"),
        (_invert_pass, "pass status does not match"),
    )
    report = RetrievalEvaluationReport.model_validate_json(RELEASE_RESULT.read_text(encoding="utf-8"))

    for mutation, message in mutations:
        data = report.model_dump(mode="json")
        mutation(data)
        with pytest.raises(ValidationError, match=message):
            RetrievalEvaluationReport.model_validate(data)
