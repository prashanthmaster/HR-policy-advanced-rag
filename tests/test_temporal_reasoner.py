"""Tests for grading/temporal_reasoner.py (T-4.3), against the real
straddle fixtures: P-01 (India gratuity ceiling, POINT_IN_TIME, do NOT
split), P-02 (India leave 18->24, SEGMENTED_ACCRUAL, DO split), P-3a
(DIFC gratuity->DEWS, SEGMENTED_ACCRUAL, DO split at 2020-02-01), P-06
(UAE end-of-service supplement, GRANDFATHERED, cohort test).

P-01 and P-3a passing together, with opposite behaviour, is the whole
point (Finding 1) -- a system that always splits or never splits fails
one of them."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from grading.temporal_reasoner import (
    ServiceFacts,
    reason_grandfathered,
    reason_over_pieces,
    reason_point_in_time,
    reason_segmented_accrual,
)
from ingestion.index_units import IndexableUnit, build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.hybrid_search import RetrievedPiece

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


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


def test_p01_india_gratuity_ceiling_does_not_split(units):
    """P-01: joined 2014-01-01, resigns 2026-09-30. Service spans the
    2018-03-29 ceiling amendment. The governing test is the trigger
    (termination/payout) date, not the service start date -- the whole
    amount is governed by the post-2018 ceiling, no split-and-blend."""
    ceiling = _piece_for(units, "IN-GRAT-S4-CEILING")
    facts = ServiceFacts(
        service_start_date=dt.date(2014, 1, 1),
        valuation_date=dt.date(2026, 9, 30),
    )
    working = reason_point_in_time(ceiling, facts)
    assert working.segments == []  # POINT_IN_TIME never produces segments
    assert working.governing_piece.clause_id == "IN-GRAT-S4-CEILING"
    joined_narrative = " ".join(working.narrative)
    assert "not get split" in joined_narrative or "not split" in joined_narrative


def test_p01_via_reason_over_pieces_does_not_invent_a_split(units):
    """Same probe through the entry point, with the superseded sibling
    ALSO in the retrieved set (as it would be after T-3.3's as-of
    resolution normally excludes it, but a defensive test should hold
    even if it leaked through) -- reason_over_pieces must still not
    produce a SEGMENTED_ACCRUAL-style split for a POINT_IN_TIME lineage."""
    ceiling = _piece_for(units, "IN-GRAT-S4-CEILING")
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30))
    workings = reason_over_pieces([ceiling], facts)
    assert len(workings) == 1
    assert workings[0].segments == []


def test_p02_india_leave_splits_and_sums(units):
    """P-02: leave rate changed 18->24 days at 2024-07-01, employee in
    service throughout. SEGMENTED_ACCRUAL: split at the boundary, one
    segment per version."""
    v1 = _piece_for(units, "MER-IN-LEAVE-ANNUAL-V1")
    v2 = _piece_for(units, "MER-IN-LEAVE-ANNUAL-V2")
    facts = ServiceFacts(service_start_date=dt.date(2020, 1, 1), valuation_date=dt.date(2026, 9, 3))
    working = reason_segmented_accrual([v1, v2], facts)
    assert len(working.segments) == 2
    assert working.segments[0].governing_piece.clause_id == "MER-IN-LEAVE-ANNUAL-V1"
    assert working.segments[0].end == dt.date(2024, 7, 1)
    assert working.segments[1].governing_piece.clause_id == "MER-IN-LEAVE-ANNUAL-V2"
    assert working.segments[1].start == dt.date(2024, 7, 1)
    assert working.missing_facts == []


def test_p3a_difc_dews_splits_at_2020_02_01(units):
    """P-3a: DIFC service since 2017, leaving 2026 -- must split at
    2020-02-01 into legacy-gratuity and DEWS segments. This is the
    contrast case to P-01: both must pass with OPPOSITE behaviour
    (Finding 1) or the system is pattern-matching, not reasoning."""
    dews = _piece_for(units, "DIFC-L2-2019-DEWS")
    legacy = _piece_for(units, "DIFC-EOSB-LEGACY-GRATUITY")
    facts = ServiceFacts(service_start_date=dt.date(2017, 1, 1), valuation_date=dt.date(2026, 9, 3))
    working = reason_segmented_accrual([dews, legacy], facts)
    assert len(working.segments) == 2
    assert working.segments[0].governing_piece.clause_id == "DIFC-EOSB-LEGACY-GRATUITY"
    assert working.segments[0].end == dt.date(2020, 2, 1)
    assert working.segments[1].governing_piece.clause_id == "DIFC-L2-2019-DEWS"
    assert working.segments[1].start == dt.date(2020, 2, 1)


def test_p01_and_p3a_pass_together_opposite_behaviour(units):
    """The actual regression this whole module exists to prevent: one
    run, both probes, opposite verdicts on whether to split."""
    ceiling = _piece_for(units, "IN-GRAT-S4-CEILING")
    dews = _piece_for(units, "DIFC-L2-2019-DEWS")
    legacy = _piece_for(units, "DIFC-EOSB-LEGACY-GRATUITY")
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30))

    p01 = reason_over_pieces([ceiling], facts)
    assert len(p01[0].segments) == 0  # no split

    difc_facts = ServiceFacts(service_start_date=dt.date(2017, 1, 1), valuation_date=dt.date(2026, 9, 3))
    p3a = reason_over_pieces([dews, legacy], difc_facts)
    assert len(p3a[0].segments) == 2  # split


def test_p06_grandfathered_cohort_test_applies(units):
    """P-06: employee's service commenced before 2025-01-01 -- the
    supplement applies."""
    topup_v2 = _piece_for(units, "MER-AE-EOS-TOPUP-V2")
    facts = ServiceFacts(service_start_date=dt.date(2022, 6, 1))
    working = reason_grandfathered(topup_v2, facts)
    assert working.governing_piece is not None
    assert working.missing_facts == []


def test_p06_grandfathered_cohort_test_does_not_apply(units):
    """Mirror case: joined after the cohort boundary -- no supplement."""
    topup_v2 = _piece_for(units, "MER-AE-EOS-TOPUP-V2")
    facts = ServiceFacts(service_start_date=dt.date(2025, 6, 1))
    working = reason_grandfathered(topup_v2, facts)
    assert working.governing_piece is None


def test_p06_without_joining_date_flags_missing_fact(units):
    """This is exactly what makes P-06 MUST_CLARIFY (Finding 5) --
    without service_start_date the cohort test cannot be resolved, and
    that gets surfaced as a missing fact, not guessed."""
    topup_v2 = _piece_for(units, "MER-AE-EOS-TOPUP-V2")
    working = reason_grandfathered(topup_v2, ServiceFacts())
    assert working.missing_facts == ["service_start_date"]
    assert working.governing_piece is None


def test_segmented_accrual_without_dates_reports_structure_not_guess(units):
    v1 = _piece_for(units, "MER-IN-LEAVE-ANNUAL-V1")
    v2 = _piece_for(units, "MER-IN-LEAVE-ANNUAL-V2")
    working = reason_segmented_accrual([v1, v2], ServiceFacts())
    assert working.segments == []
    assert set(working.missing_facts) == {"service_start_date", "valuation_date"}
