from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from generation.generator import TemplateGenerator
from grading.temporal_reasoner import (
    ServiceFacts,
    TemporalWorking,
    reason_grandfathered,
    reason_point_in_time,
    reason_segmented_accrual,
)
from ingestion.index_units import IndexableUnit, build_indexable_units
from ingestion.schema import TemporalApplicability
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


def test_p01_answer_states_no_split_with_one_citation(units):
    piece = _piece_for(units, "IN-GRAT-S4-CEILING")
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30))
    working = reason_point_in_time(piece, facts)

    answer = TemplateGenerator().generate("what gratuity do I get", [piece], [working])
    assert "does not get split" in answer.text
    assert len(answer.citations) == 1
    assert answer.citations[0].clause_id == "IN-GRAT-S4-CEILING"
    assert answer.used_temporal_reasoning is True


def test_p3a_answer_has_both_segments_and_both_citations(units):
    dews = _piece_for(units, "DIFC-L2-2019-DEWS")
    legacy = _piece_for(units, "DIFC-EOSB-LEGACY-GRATUITY")
    facts = ServiceFacts(service_start_date=dt.date(2017, 1, 1), valuation_date=dt.date(2026, 9, 3))
    working = reason_segmented_accrual([dews, legacy], facts)

    answer = TemplateGenerator().generate("what's my end of service", [dews, legacy], [working])
    assert "2020-02-01" in answer.text
    assert len(answer.citations) == 2
    cited_ids = {c.clause_id for c in answer.citations}
    assert cited_ids == {"DIFC-L2-2019-DEWS", "DIFC-EOSB-LEGACY-GRATUITY"}


def test_missing_facts_produces_no_confident_guess(units):
    topup_v2 = _piece_for(units, "MER-AE-EOS-TOPUP-V2")
    working = reason_grandfathered(topup_v2, ServiceFacts())  # no service_start_date supplied

    answer = TemplateGenerator().generate("do I get the supplement", [topup_v2], [working])
    assert "Cannot give a final answer" in answer.text
    assert "service_start_date" in answer.text


def test_no_workings_falls_back_to_raw_clause_text(units):
    piece = _piece_for(units, "IN-GRAT-S4-CEILING")
    answer = TemplateGenerator().generate("what gratuity do I get", [piece], [])
    assert piece.text in answer.text
    assert answer.used_temporal_reasoning is False

def test_p01_computes_capped_amount_when_wage_supplied(units):
    """Phase 5 addition: the deterministic arithmetic layer
    (generation/formula.py) must actually produce Rs 20,00,000 when a
    wage is supplied -- narrative-only was the gap Session 5 found and
    closed. Both the formula piece and the ceiling piece must be present
    (real P-01 shape) for the amount to be computed and capped."""
    formula = _piece_for(units, "IN-GRAT-S4-FORMULA")
    ceiling = _piece_for(units, "IN-GRAT-S4-CEILING")
    facts = ServiceFacts(
        service_start_date=dt.date(2014, 1, 1),
        valuation_date=dt.date(2026, 9, 30),
        monthly_wage=300000.0,
    )
    formula_working = reason_point_in_time(formula, facts)
    ceiling_working = reason_point_in_time(ceiling, facts)

    answer = TemplateGenerator().generate(
        "what gratuity do I get", [formula, ceiling], [formula_working, ceiling_working],
    )
    assert answer.computed_amount == 2_000_000.0
    assert "2,250,000.00" in answer.text  # uncapped figure shown too, per Finding 1's "show the working"
    assert "2,000,000.00" in answer.text
    assert "IN-GRAT-S4-CEILING" in answer.text


def test_p01_no_wage_supplied_reports_method_only_no_invented_number(units):
    """The other half of the same guarantee: with no wage, the system
    must NOT invent a figure -- computed_amount stays None."""
    formula = _piece_for(units, "IN-GRAT-S4-FORMULA")
    ceiling = _piece_for(units, "IN-GRAT-S4-CEILING")
    facts = ServiceFacts(service_start_date=dt.date(2014, 1, 1), valuation_date=dt.date(2026, 9, 30))
    formula_working = reason_point_in_time(formula, facts)
    ceiling_working = reason_point_in_time(ceiling, facts)

    answer = TemplateGenerator().generate(
        "what gratuity do I get", [formula, ceiling], [formula_working, ceiling_working],
    )
    assert answer.computed_amount is None
    assert "requires a monthly wage" in answer.text


def test_p01_wage_below_ceiling_is_not_capped(units):
    """The ceiling must only bite when it actually would -- proves the
    cap logic isn't a blanket clamp, per the same discipline as
    docs/DELIBERATE_DEFECTS.md's other trap fixtures."""
    formula = _piece_for(units, "IN-GRAT-S4-FORMULA")
    ceiling = _piece_for(units, "IN-GRAT-S4-CEILING")
    facts = ServiceFacts(
        service_start_date=dt.date(2020, 1, 1),
        valuation_date=dt.date(2023, 1, 1),
        monthly_wage=50000.0,
    )
    formula_working = reason_point_in_time(formula, facts)
    ceiling_working = reason_point_in_time(ceiling, facts)

    answer = TemplateGenerator().generate(
        "what gratuity do I get", [formula, ceiling], [formula_working, ceiling_working],
    )
    # 3 completed years (exactly 36 months, no >6-month remainder), (50000/26)*15*3
    expected = (50000.0 / 26) * 15 * 3
    assert answer.computed_amount == pytest.approx(expected)
    assert answer.computed_amount < 1_000_000.0  # nowhere near either ceiling


def test_p03_computes_uae_tenure_banded_day_count_no_rupee_figure(units):
    """P-03's shape: tenure-banded days computed, but no rupee amount --
    UAE's daily-wage divisor was never verified in this project, so the
    calculator must not assert one. UAE-DL33-ART51-GRATUITY-FORMULA is
    tagged SEGMENTED_ACCRUAL with no amendment pair -- this constructs
    the same self-contained TemporalWorking reason_over_pieces' fallback
    branch would (see grading/temporal_reasoner.py), since generate()'s
    formula lookup keys off governing_piece.clause_id, not applicability."""
    formula = _piece_for(units, "UAE-DL33-ART51-GRATUITY-FORMULA")
    facts = ServiceFacts(
        service_start_date=dt.date(2019, 1, 1),
        valuation_date=dt.date(2026, 1, 1),
        monthly_wage=15000.0,  # supplied on purpose -- must still not produce a rupee figure
    )
    working = TemporalWorking(
        applicability=TemporalApplicability.SEGMENTED_ACCRUAL,
        narrative=[f"{formula.clause_id} is self-contained, tenure-banded."],
        governing_piece=formula,
        service_start_date=facts.service_start_date,
        valuation_date=facts.valuation_date,
        monthly_wage=facts.monthly_wage,
    )

    answer = TemplateGenerator().generate("how is my end of service calculated", [formula], [working])
    assert answer.computed_days == 165.0
    assert answer.computed_amount is None


def test_p02_computes_segmented_leave_days(units):
    """P-02's shape: segmented accrual sums each segment's own rate."""
    v1 = _piece_for(units, "MER-IN-LEAVE-ANNUAL-V1")
    v2 = _piece_for(units, "MER-IN-LEAVE-ANNUAL-V2")
    facts = ServiceFacts(service_start_date=dt.date(2022, 1, 1), valuation_date=dt.date(2026, 9, 3))
    working = reason_segmented_accrual([v1, v2], facts)

    answer = TemplateGenerator().generate("how many leave days did I accrue", [v1, v2], [working])
    assert answer.computed_days == pytest.approx(97.0)
