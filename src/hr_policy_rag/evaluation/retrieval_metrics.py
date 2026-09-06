"""Deterministic source-level metrics for the frozen retrieval exam."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import Field

from hr_policy_rag.corpus import ManifestSource
from hr_policy_rag.domain import Evidence
from hr_policy_rag.domain.models import ContractModel, NonEmptyString
from hr_policy_rag.evaluation.retrieval_cases import RetrievalCase, RetrievalThresholds


class RetrievalCaseScore(ContractModel):
    case_id: NonEmptyString
    returned_source_ids: tuple[NonEmptyString, ...]
    target_recall: float = Field(ge=0, le=1)
    reciprocal_rank: float = Field(ge=0, le=1)
    temporal_correct: bool
    filter_leakage_count: int = Field(ge=0)
    error_code: NonEmptyString | None = None


class RetrievalAggregate(ContractModel):
    case_count: int = Field(gt=0)
    recall_at_10: float = Field(ge=0, le=1)
    reciprocal_rank_at_10: float = Field(ge=0, le=1)
    temporal_accuracy: float = Field(ge=0, le=1)
    filter_leakage: float = Field(ge=0, le=1)
    errors: int = Field(ge=0)
    exclusions: int = Field(ge=0)


def score_case(
    case: RetrievalCase,
    evidence: Sequence[Evidence],
    sources: Mapping[str, ManifestSource],
    *,
    error_code: str | None = None,
) -> RetrievalCaseScore:
    source_ids = tuple(item.source_id for item in evidence[:10])
    hit_groups = sum(any(source_id in source_ids for source_id in group) for group in case.required_source_groups)
    targets = {source_id for group in case.required_source_groups for source_id in group}
    first_rank = next((rank for rank, source_id in enumerate(source_ids, start=1) if source_id in targets), None)
    leakage = 0
    for item in evidence[:10]:
        source = sources.get(item.source_id)
        if (
            source is None
            or source.jurisdiction not in {case.jurisdiction, "GLOBAL"}
            or case.topic not in source.topics
            or source.effective_from is None
            or source.effective_from > case.as_of_date
            or (source.effective_to is not None and case.as_of_date >= source.effective_to)
        ):
            leakage += 1
    temporal_correct = not bool(set(source_ids) & set(case.forbidden_source_ids))
    return RetrievalCaseScore(
        case_id=case.case_id,
        returned_source_ids=source_ids,
        target_recall=hit_groups / len(case.required_source_groups),
        reciprocal_rank=0 if first_rank is None else 1 / first_rank,
        temporal_correct=temporal_correct,
        filter_leakage_count=leakage,
        error_code=error_code,
    )


def aggregate_scores(scores: Sequence[RetrievalCaseScore]) -> RetrievalAggregate:
    if not scores:
        raise ValueError("cannot aggregate an empty retrieval result")
    result_count = sum(len(score.returned_source_ids) for score in scores)
    return RetrievalAggregate(
        case_count=len(scores),
        recall_at_10=sum(score.target_recall for score in scores) / len(scores),
        reciprocal_rank_at_10=sum(score.reciprocal_rank for score in scores) / len(scores),
        temporal_accuracy=sum(score.temporal_correct for score in scores) / len(scores),
        filter_leakage=(sum(score.filter_leakage_count for score in scores) / result_count if result_count else 0),
        errors=sum(score.error_code is not None for score in scores),
        exclusions=0,
    )


def passes_thresholds(
    aggregate: RetrievalAggregate,
    thresholds: RetrievalThresholds,
    slice_aggregates: Sequence[RetrievalAggregate],
) -> bool:
    return (
        aggregate.recall_at_10 >= thresholds.recall_at_10
        and aggregate.reciprocal_rank_at_10 >= thresholds.reciprocal_rank_at_10
        and aggregate.temporal_accuracy >= thresholds.temporal_accuracy
        and aggregate.filter_leakage <= thresholds.maximum_filter_leakage
        and aggregate.errors <= thresholds.maximum_errors
        and aggregate.exclusions <= thresholds.maximum_exclusions
        and all(item.recall_at_10 >= thresholds.minimum_slice_recall_at_10 for item in slice_aggregates)
    )
