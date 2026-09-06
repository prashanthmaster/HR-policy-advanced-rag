from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from pydantic import HttpUrl, ValidationError

from hr_policy_rag.domain import (
    Answer,
    AnswerStatus,
    CaseFacts,
    Claim,
    Clause,
    Decision,
    DecisionStatus,
    NormativeTier,
    PolicyTopic,
    RunManifest,
    SourceDocument,
    SourceStatus,
)

_SHA256 = "a" * 64


def _clause(
    *,
    effective_to: dt.date | None = None,
    supersedes: tuple[str, ...] = (),
) -> Clause:
    return Clause(
        clause_id="notice-v2",
        source_id="policy-uae",
        section="Notice",
        text="The notice period is 30 days.",
        locator="paragraph:7",
        jurisdiction="UAE",
        normative_tier=NormativeTier.COMPANY_POLICY,
        effective_from=dt.date(2026, 1, 1),
        effective_to=effective_to,
        supersedes=supersedes,
    )


def test_statutory_source_requires_real_provenance() -> None:
    with pytest.raises(ValidationError, match="authoritative source_url"):
        SourceDocument(
            source_id="uae-law-33",
            title="UAE Labour Law",
            jurisdiction="UAE",
            normative_tier=NormativeTier.STATUTORY,
            version="2021",
            content_sha256=_SHA256,
            status=SourceStatus.APPROVED,
            synthetic=False,
            retrieved_at=dt.datetime(2026, 9, 6, tzinfo=dt.UTC),
        )

    with pytest.raises(ValidationError, match="cannot be marked synthetic"):
        SourceDocument(
            source_id="uae-law-33",
            title="UAE Labour Law",
            jurisdiction="UAE",
            normative_tier=NormativeTier.STATUTORY,
            version="2021",
            content_sha256=_SHA256,
            status=SourceStatus.APPROVED,
            synthetic=True,
            source_url=HttpUrl("https://example.gov/uae-law-33"),
            retrieved_at=dt.datetime(2026, 9, 6, tzinfo=dt.UTC),
        )


def test_clause_rejects_invalid_temporal_range_and_self_supersession() -> None:
    with pytest.raises(ValidationError, match="effective_to"):
        _clause(effective_to=dt.date(2025, 12, 31))
    with pytest.raises(ValidationError, match="supersede itself"):
        _clause(supersedes=("notice-v2",))
    with pytest.raises(ValidationError, match="duplicate clause IDs"):
        _clause(supersedes=("notice-v1", "notice-v1"))


def test_case_facts_require_currency_and_coherent_dates() -> None:
    with pytest.raises(ValidationError, match="currency"):
        CaseFacts(monthly_wage=Decimal("12000"))
    with pytest.raises(ValidationError, match="service_start_date"):
        CaseFacts(
            as_of_date=dt.date(2025, 1, 1),
            service_start_date=dt.date(2025, 1, 2),
        )
    facts = CaseFacts(monthly_wage=Decimal("12000"), currency="AED")
    assert facts.currency == "AED"
    scoped = CaseFacts(country="UAE", topic=PolicyTopic.NOTICE, as_of_date=dt.date(2026, 8, 1))
    assert scoped.topic is PolicyTopic.NOTICE


def test_decision_requires_evidence_or_missing_facts_for_its_status() -> None:
    with pytest.raises(ValidationError, match="requires evidence"):
        Decision(status=DecisionStatus.ANSWERABLE)
    with pytest.raises(ValidationError, match="requires missing facts"):
        Decision(status=DecisionStatus.NEEDS_CLARIFICATION)
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        Decision(status=DecisionStatus.ANSWERABLE, evidence_ids=("e-1", "e-1"))


def test_material_claim_cannot_be_uncited() -> None:
    with pytest.raises(ValidationError, match="requires evidence"):
        Claim(claim_id="claim-1", text="Notice is 30 days.")


def test_answered_response_requires_supported_claims() -> None:
    claim = Claim(
        claim_id="claim-1",
        text="Notice is 30 days.",
        evidence_ids=("evidence-1",),
    )
    answer = Answer(
        status=AnswerStatus.ANSWERED,
        text="The governing notice period is 30 days.",
        claims=(claim,),
        trace_id="trace-1",
    )
    assert answer.claims == (claim,)

    with pytest.raises(ValidationError, match="requires text"):
        Answer(status=AnswerStatus.ANSWERED, trace_id="trace-missing")

    with pytest.raises(ValidationError, match="cannot contain claims"):
        Answer(
            status=AnswerStatus.UNVERIFIED,
            text="Validation failed.",
            claims=(claim,),
            trace_id="trace-2",
        )


def test_run_manifest_rejects_out_of_range_threshold() -> None:
    with pytest.raises(ValidationError, match="between 0 and 1"):
        RunManifest(
            run_id="run-1",
            git_sha="abc123",
            lockfile_sha256=_SHA256,
            corpus_sha256=_SHA256,
            index_generation="index-1",
            evaluation_date=dt.date(2026, 9, 6),
            random_seed=42,
            model_versions={"embedding": "model-1"},
            prompt_versions={"answer": "prompt-1"},
            thresholds={"recall": 1.1},
            estimated_cost_usd=Decimal("0.10"),
        )
