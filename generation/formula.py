"""
Phase 5 addition: minimal deterministic arithmetic on top of T-4.3's
structural temporal reasoning.

Context (see PROJECT_PLAN.md / slot4_progress.md Session 5): building the
Phase 5 golden-set eval surfaced that TemplateGenerator never actually
computed a number -- grading/temporal_reasoner.py does the STRUCTURAL
reasoning only (which version/segment governs), by its own docstring, and
the arithmetic that docstring assigns to generation (T-4.4) was never
built. That's a real gap against a golden set whose answers include a
figure (P-01's Rs 20,00,000, P-02's ~97 accrued days, P-03's 165-day
tenure-banded total), and against the project's own marquee pitch
("walk me through the calculation").

This module is deliberately narrow, not a general prose-formula parser --
same scoping discipline as temporal_reasoner.py's cohort_rule regex and
its documented ELECTIVE-has-no-real-fixture gap. It hardcodes a small
lookup table keyed by clause_id, covering exactly the formula-bearing
clauses the scored golden set exercises. Extending it to a new clause
means adding one table entry, not writing a parser for arbitrary legal
prose -- prose formulas are natural language, not a grammar worth
building a general parser for at this scale.

Deliberately NOT covered: DIFC DEWS contribution-rate accrual (P-3a).
Real DEWS accounting involves contribution-timing and possibly
compounding assumptions never verified against a primary source in this
project -- computing a rupee figure for it would be inventing an
unverified number, which the project's standing rule forbids. P-3a's
golden answer already scores on "state both components separately, don't
blend them," which the existing narrative-only behaviour satisfies
without arithmetic.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


# --- date arithmetic -----------------------------------------------------


def months_between(start: dt.date, end: dt.date) -> int:
    """Whole completed months from start to end, day-of-month aware:
    2024-07-01 -> 2026-09-03 is 26 months (the 3rd is on/after the 1st,
    so the partial final month still counts), but 2024-07-15 -> 2026-09-03
    is 25 (the 3rd is before the 15th, so the last month isn't complete).
    Matches the corpus's own "accruing proportionately month by month"
    phrasing (MER-IN-LEAVE-ANNUAL-V1/V2) -- a day-fraction convention was
    never stated in any clause, so this doesn't invent one."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def completed_years_indian_rule(start: dt.date, end: dt.date) -> int:
    """Payment of Gratuity Act 1972 s.4(2)'s own rounding rule, restated
    verbatim in MER-IN-GRATUITY-ENTITLEMENT: "a part of a year in excess
    of six months being reckoned as a completed year." Validated by hand
    against P-01's own stated figures: 2014-01-01 -> 2026-09-30 gives 152
    total months -> 12 years + 8 remainder months -> remainder > 6 ->
    13 completed years, matching adversarial_probe_set.md's marquee
    probe exactly."""
    total_months = months_between(start, end)
    years, remainder_months = divmod(total_months, 12)
    if remainder_months > 6:
        years += 1
    return years


# --- formula / ceiling tables ---------------------------------------------


@dataclass(frozen=True)
class Ceiling:
    clause_id: str
    kind: str  # "fixed_amount" | "years_of_wage"
    value: float
    """Rupees (or the relevant currency's smallest-quoted-unit-of-account)
    for fixed_amount; number of years for years_of_wage."""


@dataclass(frozen=True)
class Formula:
    clause_id: str
    kind: str  # "flat_days_per_year" | "tenure_banded_days_per_year" | "flat_days_per_year_proportional"
    days_per_year: float | None = None
    """Set for flat_days_per_year and flat_days_per_year_proportional."""
    bands: tuple[tuple[float, float | None, float], ...] = ()
    """Set for tenure_banded_days_per_year: (from_year, to_year_or_None, days_per_year) triples, in order."""
    wage_divisor: int | None = None
    """Divide monthly wage by this to get a daily rate, e.g. India's 26.
    None means "day-count only, no verified wage convention" -- see
    UAE-DL33-ART51-GRATUITY-FORMULA's entry below."""
    ceiling_clause_ids: tuple[str, ...] = ()
    rounding: str = "none"  # "indian_gratuity" | "none"


CEILINGS: dict[str, Ceiling] = {
    "IN-GRAT-S4-CEILING": Ceiling("IN-GRAT-S4-CEILING", "fixed_amount", 2_000_000.0),
    "IN-GRAT-S4-CEILING-SUPERSEDED": Ceiling("IN-GRAT-S4-CEILING-SUPERSEDED", "fixed_amount", 1_000_000.0),
    "UAE-DL33-ART51-CEILING": Ceiling("UAE-DL33-ART51-CEILING", "years_of_wage", 2.0),
}

FORMULAS: dict[str, Formula] = {
    "IN-GRAT-S4-FORMULA": Formula(
        "IN-GRAT-S4-FORMULA", "flat_days_per_year",
        days_per_year=15.0, wage_divisor=26,
        ceiling_clause_ids=("IN-GRAT-S4-CEILING", "IN-GRAT-S4-CEILING-SUPERSEDED"),
        rounding="indian_gratuity",
    ),
    "UAE-DL33-ART51-GRATUITY-FORMULA": Formula(
        "UAE-DL33-ART51-GRATUITY-FORMULA", "tenure_banded_days_per_year",
        bands=((0.0, 5.0, 21.0), (5.0, None, 30.0)),
        wage_divisor=None,  # UAE's daily-wage divisor (per-30 vs per-26) was never verified this
                            # project -- day-count only, never assert an unverified rupee figure.
        ceiling_clause_ids=("UAE-DL33-ART51-CEILING",),
        rounding="none",
    ),
    "MER-IN-LEAVE-ANNUAL-V1": Formula(
        "MER-IN-LEAVE-ANNUAL-V1", "flat_days_per_year_proportional", days_per_year=18.0,
    ),
    "MER-IN-LEAVE-ANNUAL-V2": Formula(
        "MER-IN-LEAVE-ANNUAL-V2", "flat_days_per_year_proportional", days_per_year=24.0,
    ),
}


@dataclass
class Computation:
    total_days: float | None = None
    amount: float | None = None
    ceiling_applied: str | None = None
    """clause_id of the ceiling that capped the amount, if any."""
    uncapped_amount: float | None = None
    note: str | None = None


def _apply_ceiling(amount: float, formula: Formula, pieces_clause_ids: set[str]) -> tuple[float, str | None]:
    for ceiling_id in formula.ceiling_clause_ids:
        if ceiling_id in pieces_clause_ids:
            ceiling = CEILINGS.get(ceiling_id)
            if ceiling is None or ceiling.kind != "fixed_amount":
                continue
            if amount > ceiling.value:
                return ceiling.value, ceiling_id
    return amount, None


def compute_flat_gratuity(
    formula: Formula, start: dt.date, end: dt.date,
    monthly_wage: float | None, pieces_clause_ids: set[str],
) -> Computation:
    """IN-GRAT-S4-FORMULA's shape: (wage / divisor) * days_per_year * completed_years, capped."""
    if formula.rounding == "indian_gratuity":
        years = completed_years_indian_rule(start, end)
    else:
        years = months_between(start, end) / 12.0

    if monthly_wage is None or formula.wage_divisor is None:
        return Computation(note=f"{years:g} completed years -- amount requires a monthly wage to compute.")

    daily_rate = monthly_wage / formula.wage_divisor
    uncapped = daily_rate * formula.days_per_year * years
    capped, ceiling_id = _apply_ceiling(uncapped, formula, pieces_clause_ids)
    return Computation(amount=capped, uncapped_amount=uncapped, ceiling_applied=ceiling_id)


def compute_tenure_banded_days(formula: Formula, start: dt.date, end: dt.date) -> Computation:
    """UAE-DL33-ART51-GRATUITY-FORMULA's shape: sum days_per_year across
    tenure bands. Day-count only -- see the formula table's note on why
    no rupee figure is computed here."""
    tenure_years = months_between(start, end) / 12.0
    total_days = 0.0
    for band_start, band_end, rate in formula.bands:
        if tenure_years <= band_start:
            continue
        this_band_years = min(tenure_years, band_end) - band_start if band_end is not None else tenure_years - band_start
        this_band_years = max(this_band_years, 0.0)
        total_days += this_band_years * rate
    return Computation(total_days=total_days, note="Day-count only -- UAE's daily-wage divisor convention was never verified in this project.")


def compute_leave_segment(formula: Formula, start: dt.date, end: dt.date) -> float:
    """One segment of MER-IN-LEAVE-ANNUAL-V1/V2's proportional accrual:
    days_per_year/12 per completed month."""
    months = months_between(start, end)
    return (formula.days_per_year / 12.0) * months
