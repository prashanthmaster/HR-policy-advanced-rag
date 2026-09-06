"""Canonical immutable domain models.

These contracts deliberately contain no framework, storage, or model-provider
types. Every adapter must translate at its boundary instead of leaking an
integration-specific schema into policy logic.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class ContractModel(BaseModel):
    """Strict, immutable base for data crossing architectural boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class NormativeTier(StrEnum):
    STATUTORY = "STATUTORY"
    COMPANY_POLICY = "COMPANY_POLICY"


class SourceStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


class SourceDocument(ContractModel):
    source_id: NonEmptyString
    title: NonEmptyString
    jurisdiction: NonEmptyString
    normative_tier: NormativeTier
    version: NonEmptyString
    content_sha256: Sha256
    status: SourceStatus
    synthetic: bool
    source_url: HttpUrl | None = None
    published_at: dt.datetime | None = None
    retrieved_at: dt.datetime

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        if self.normative_tier is NormativeTier.STATUTORY and self.synthetic:
            raise ValueError("statutory sources cannot be marked synthetic")
        if self.normative_tier is NormativeTier.STATUTORY and self.source_url is None:
            raise ValueError("statutory sources require an authoritative source_url")
        return self


class Clause(ContractModel):
    clause_id: NonEmptyString
    source_id: NonEmptyString
    section: NonEmptyString
    text: NonEmptyString
    locator: NonEmptyString
    jurisdiction: NonEmptyString
    normative_tier: NormativeTier
    effective_from: dt.date
    effective_to: dt.date | None = None
    supersedes: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def validate_temporal_range(self) -> Self:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        if self.clause_id in self.supersedes:
            raise ValueError("a clause cannot supersede itself")
        if len(set(self.supersedes)) != len(self.supersedes):
            raise ValueError("supersedes must not contain duplicate clause IDs")
        return self


class Evidence(ContractModel):
    evidence_id: NonEmptyString
    clause_id: NonEmptyString
    source_id: NonEmptyString
    corpus_generation: NonEmptyString
    quote: NonEmptyString
    locator: NonEmptyString
    retrieval_score: float = Field(ge=0, allow_inf_nan=False)


class CaseFacts(ContractModel):
    country: NonEmptyString | None = None
    jurisdiction_scope: NonEmptyString | None = None
    as_of_date: dt.date | None = None
    service_start_date: dt.date | None = None
    monthly_wage: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    currency: CurrencyCode | None = None
    employee_category: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_case(self) -> Self:
        if self.monthly_wage is not None and self.currency is None:
            raise ValueError("currency is required when monthly_wage is provided")
        if (
            self.service_start_date is not None
            and self.as_of_date is not None
            and self.service_start_date > self.as_of_date
        ):
            raise ValueError("service_start_date cannot be later than as_of_date")
        return self


class DecisionStatus(StrEnum):
    ANSWERABLE = "ANSWERABLE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Decision(ContractModel):
    status: DecisionStatus
    evidence_ids: tuple[NonEmptyString, ...] = ()
    missing_facts: tuple[NonEmptyString, ...] = ()
    calculation_ids: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        for field_name in ("evidence_ids", "missing_facts", "calculation_ids", "warnings"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        if self.status is DecisionStatus.ANSWERABLE and not self.evidence_ids:
            raise ValueError("an answerable decision requires evidence")
        if self.status is DecisionStatus.NEEDS_CLARIFICATION and not self.missing_facts:
            raise ValueError("a clarification decision requires missing facts")
        return self


class Claim(ContractModel):
    claim_id: NonEmptyString
    text: NonEmptyString
    material: bool = True
    evidence_ids: tuple[NonEmptyString, ...] = ()
    calculation_ids: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def validate_support(self) -> Self:
        if self.material and not (self.evidence_ids or self.calculation_ids):
            raise ValueError("a material claim requires evidence or a deterministic calculation")
        return self


class AnswerStatus(StrEnum):
    ANSWERED = "ANSWERED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    BLOCKED_INPUT = "BLOCKED_INPUT"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    UNVERIFIED = "UNVERIFIED"


class Answer(ContractModel):
    status: AnswerStatus
    text: NonEmptyString | None = None
    claims: tuple[Claim, ...] = ()
    limitations: tuple[NonEmptyString, ...] = ()
    trace_id: NonEmptyString

    @model_validator(mode="after")
    def validate_answer(self) -> Self:
        if self.status is AnswerStatus.ANSWERED and (self.text is None or not self.claims):
            raise ValueError("an answered response requires text and at least one claim")
        if self.status is not AnswerStatus.ANSWERED and self.claims:
            raise ValueError("non-answered responses cannot contain claims")
        return self


class IndexManifest(ContractModel):
    index_generation: NonEmptyString
    corpus_generation: NonEmptyString
    corpus_sha256: Sha256
    collection_name: NonEmptyString
    embedding_model: NonEmptyString
    embedding_dimensions: int = Field(gt=0)
    sparse_model: NonEmptyString
    point_count: int = Field(ge=0)
    created_at: dt.datetime


class RunManifest(ContractModel):
    run_id: NonEmptyString
    git_sha: NonEmptyString
    lockfile_sha256: Sha256
    corpus_sha256: Sha256
    index_generation: NonEmptyString
    evaluation_date: dt.date
    random_seed: int
    model_versions: dict[NonEmptyString, NonEmptyString]
    prompt_versions: dict[NonEmptyString, NonEmptyString]
    thresholds: dict[NonEmptyString, float]
    estimated_cost_usd: Decimal = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        invalid = {name: value for name, value in self.thresholds.items() if not 0 <= value <= 1}
        if invalid:
            raise ValueError("thresholds must be between 0 and 1")
        return self
