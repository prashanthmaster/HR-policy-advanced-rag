"""Tests for generation/formula.py's pure date/arithmetic helpers --
these are the same numbers Session 5 verified by hand before wiring the
calculator into TemplateGenerator (see slot4_progress.md)."""

from __future__ import annotations

import datetime as dt

from generation.formula import (
    FORMULAS,
    compute_flat_gratuity,
    compute_leave_segment,
    compute_tenure_banded_days,
    completed_years_indian_rule,
    months_between,
)


def test_months_between_whole_months():
    assert months_between(dt.date(2024, 7, 1), dt.date(2026, 9, 3)) == 26


def test_months_between_day_of_month_matters():
    # the 3rd is before the 15th, so the final partial month doesn't count
    assert months_between(dt.date(2024, 7, 15), dt.date(2026, 9, 3)) == 25


def test_completed_years_indian_rule_matches_p01_marquee_probe():
    """2014-01-01 -> 2026-09-30: probe doc states 13 completed years."""
    assert completed_years_indian_rule(dt.date(2014, 1, 1), dt.date(2026, 9, 30)) == 13


def test_completed_years_indian_rule_remainder_of_exactly_six_months_does_not_round_up():
    # the Act's own wording is "in excess of six months" -- exactly six must not round up
    assert completed_years_indian_rule(dt.date(2020, 1, 1), dt.date(2023, 7, 1)) == 3


def test_compute_flat_gratuity_p01_capped():
    formula = FORMULAS["IN-GRAT-S4-FORMULA"]
    comp = compute_flat_gratuity(
        formula, dt.date(2014, 1, 1), dt.date(2026, 9, 30), 300000.0, {"IN-GRAT-S4-CEILING"},
    )
    assert comp.uncapped_amount == 2_250_000.0
    assert comp.amount == 2_000_000.0
    assert comp.ceiling_applied == "IN-GRAT-S4-CEILING"


def test_compute_flat_gratuity_no_wage_reports_years_only():
    formula = FORMULAS["IN-GRAT-S4-FORMULA"]
    comp = compute_flat_gratuity(
        formula, dt.date(2014, 1, 1), dt.date(2026, 9, 30), None, {"IN-GRAT-S4-CEILING"},
    )
    assert comp.amount is None
    assert "13" in comp.note


def test_compute_flat_gratuity_ceiling_absent_from_pieces_is_not_applied():
    """The ceiling must come from what was actually retrieved, not be
    assumed present -- same discipline as the rest of the project's
    'never cite what wasn't retrieved' rule."""
    formula = FORMULAS["IN-GRAT-S4-FORMULA"]
    comp = compute_flat_gratuity(
        formula, dt.date(2014, 1, 1), dt.date(2026, 9, 30), 300000.0, set(),
    )
    assert comp.amount == 2_250_000.0
    assert comp.ceiling_applied is None


def test_compute_tenure_banded_days_p03():
    formula = FORMULAS["UAE-DL33-ART51-GRATUITY-FORMULA"]
    comp = compute_tenure_banded_days(formula, dt.date(2019, 1, 1), dt.date(2026, 1, 1))
    assert comp.total_days == 165.0


def test_compute_tenure_banded_days_under_five_years_uses_only_first_band():
    formula = FORMULAS["UAE-DL33-ART51-GRATUITY-FORMULA"]
    comp = compute_tenure_banded_days(formula, dt.date(2023, 1, 1), dt.date(2026, 1, 1))
    assert comp.total_days == 63.0  # 3 years * 21


def test_compute_leave_segment_p02():
    v1 = FORMULAS["MER-IN-LEAVE-ANNUAL-V1"]
    v2 = FORMULAS["MER-IN-LEAVE-ANNUAL-V2"]
    d1 = compute_leave_segment(v1, dt.date(2022, 1, 1), dt.date(2024, 7, 1))
    d2 = compute_leave_segment(v2, dt.date(2024, 7, 1), dt.date(2026, 9, 3))
    assert d1 == 45.0
    assert d2 == 52.0
