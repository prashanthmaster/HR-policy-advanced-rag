from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from generation.generator import TemplateGenerator
from grading.temporal_reasoner import (
    ServiceFacts,
    reason_grandfathered,
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