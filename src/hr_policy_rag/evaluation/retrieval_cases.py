"""Strict contracts and loading for the frozen retrieval evaluation."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Self, cast

from pydantic import Field, model_validator

from hr_policy_rag.domain.models import ContractModel, NonEmptyString, Sha256


class RetrievalSplit(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    REGRESSION = "REGRESSION"
    HOLDOUT = "HOLDOUT"


class RetrievalThresholds(ContractModel):
    recall_at_10: float = Field(ge=0, le=1)
    minimum_slice_recall_at_10: float = Field(ge=0, le=1)
    reciprocal_rank_at_10: float = Field(ge=0, le=1)
    temporal_accuracy: float = Field(ge=0, le=1)
    maximum_filter_leakage: float = Field(ge=0, le=1)
    maximum_errors: int = Field(ge=0)
    maximum_exclusions: int = Field(ge=0)


class RetrievalCase(ContractModel):
    case_id: NonEmptyString
    split: RetrievalSplit
    query: NonEmptyString
    jurisdiction: NonEmptyString
    topic: NonEmptyString
    as_of_date: dt.date
    required_source_groups: tuple[tuple[NonEmptyString, ...], ...]
    forbidden_source_ids: tuple[NonEmptyString, ...] = ()
    rationale: NonEmptyString

    @model_validator(mode="after")
    def validate_targets(self) -> Self:
        if not self.required_source_groups:
            raise ValueError("each retrieval case requires at least one target group")
        if any(not group for group in self.required_source_groups):
            raise ValueError("target groups cannot be empty")
        flattened = [source_id for group in self.required_source_groups for source_id in group]
        if len(flattened) != len(set(flattened)):
            raise ValueError("target source IDs must be unique within a case")
        if set(flattened) & set(self.forbidden_source_ids):
            raise ValueError("a source cannot be both required and forbidden")
        if len(self.forbidden_source_ids) != len(set(self.forbidden_source_ids)):
            raise ValueError("forbidden source IDs must be unique")
        return self


class RetrievalCaseSet(ContractModel):
    schema_version: int = Field(ge=1)
    frozen_on: dt.date
    corpus_generation: NonEmptyString
    thresholds: RetrievalThresholds
    cases_sha256: Sha256
    cases: tuple[RetrievalCase, ...]

    @model_validator(mode="after")
    def validate_cases(self) -> Self:
        if not self.cases:
            raise ValueError("retrieval case set cannot be empty")
        case_ids = [case.case_id for case in self.cases]
        queries = [case.query.casefold() for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("retrieval case IDs must be unique")
        if len(queries) != len(set(queries)):
            raise ValueError("retrieval queries must be unique")
        return self


def _canonical_cases_bytes(cases: list[object]) -> bytes:
    return (json.dumps(cases, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_retrieval_case_set(path: Path) -> RetrievalCaseSet:
    """Load the frozen case set and verify its independent content digest."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load retrieval case set: {path}") from exc
    if not isinstance(raw, dict):
        raise ValueError("retrieval case set must contain a cases array")
    raw_object = cast(dict[str, object], raw)
    cases = raw_object.get("cases")
    if not isinstance(cases, list):
        raise ValueError("retrieval case set must contain a cases array")
    expected = hashlib.sha256(_canonical_cases_bytes(cast(list[object], cases))).hexdigest()
    if raw_object.get("cases_sha256") != expected:
        raise ValueError("retrieval cases digest mismatch")
    return RetrievalCaseSet.model_validate(raw_object)
