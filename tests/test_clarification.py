"""Tests for grading/clarification.py (T-4.5), against real corpus
fixtures where possible (P-06's grandfathered joining-date gap), and a
synthetic pair for the country-ambiguity trigger (P-13/P-19/P-41's
shape) since that needs two same-topic clauses from different countries
side by side, which no single real clause pair conveniently is."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from generation.generator import TemplateGenerator
from grading.clarification import build_clarification, detect_missing_facts
from grading.schema import GradeVerdict
from grading.temporal_reasoner import ServiceFacts, reason_grandfathered
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


def test_p06_missing_joining_date_is_detected(units):
    """P-06's shape: GRANDFATHERED clause, no service_start_date supplied
    -- T-4.3 already flags this in TemporalWorking.missing_facts;
    detect_missing_facts must surface it as a MissingFact with a reason."""
    topup_v2 = _piece_for(units, "MER-AE-EOS-TOPUP-V2")
    working = reason_grandfathered(topup_v2, ServiceFacts())

    missing = detect_missing_facts([topup_v2], [working], query_country="UAE")
    fact_names = {m.fact for m in missing}
    assert "service_start_date" in fact_names
    assert "country" not in fact_names  # country WAS supplied here
    entry = next(m for m in missing if m.fact == "service_start_date")
    assert "cohort" in entry.why.lower() or "service" in entry.why.lower()


def test_p06_clarification_response_has_no_conditional_branches(units):
    """A missing date isn't a small enumerable set -- build_clarification
    should report the missing fact but not fabricate branches for it."""
    topup_v2 = _piece_for(units, "MER-AE-EOS-TOPUP-V2")
    working = reason_grandfathered(topup_v2, ServiceFacts())
    missing = detect_missing_facts([topup_v2], [working], query_country="UAE")

    response = build_clarification("do I get the supplement", [topup_v2], [working], missing)
    assert response.status == "NEEDS_CLARIFICATION"
    assert len(response.missing_facts) == 1
    assert response.conditional_answers == []


def test_no_country_and_multiple_countries_retrieved_is_ambiguous(units):
    """P-13/P-19/P-41's shape: no country stated, and the retrieved
    normative clauses answer differently by country -- must not silently
    default to one (P-41's exact trap: the corpus is India-heavy)."""
    india_notice = next(p for p in units if p.country == "India" and p.normative and p.doc_type == "policy")
    uae_notice = next(p for p in units if p.country == "UAE" and p.normative and p.doc_type == "policy")
    pieces = [
        RetrievedPiece(piece_id=india_notice.piece_id, clause_id=india_notice.clause_id, text=india_notice.text, fused_score=1.0, rerank_score=1.0, unit=india_notice),
        RetrievedPiece(piece_id=uae_notice.piece_id, clause_id=uae_notice.clause_id, text=uae_notice.text, fused_score=1.0, rerank_score=1.0, unit=uae_notice),
    ]

    missing = detect_missing_facts(pieces, [], query_country=None)
    assert any(m.fact == "country" for m in missing)


def test_country_supplied_is_not_ambiguous(units):
    """Same two pieces, but the caller DID supply a country -- retrieval
    should already have filtered to it in practice, but even if a
    cross-country piece leaked through, an explicit query_country means
    this isn't the silent-pick failure being guarded against."""
    india_notice = next(p for p in units if p.country == "India" and p.normative and p.doc_type == "policy")
    uae_notice = next(p for p in units if p.country == "UAE" and p.normative and p.doc_type == "policy")
    pieces = [
        RetrievedPiece(piece_id=india_notice.piece_id, clause_id=india_notice.clause_id, text=india_notice.text, fused_score=1.0, rerank_score=1.0, unit=india_notice),
        RetrievedPiece(piece_id=uae_notice.piece_id, clause_id=uae_notice.clause_id, text=uae_notice.text, fused_score=1.0, rerank_score=1.0, unit=uae_notice),
    ]
    missing = detect_missing_facts(pieces, [], query_country="India")
    assert not any(m.fact == "country" for m in missing)


def test_country_ambiguity_produces_one_conditional_answer_per_country(units):
    india_notice = next(p for p in units if p.country == "India" and p.normative and p.doc_type == "policy")
    uae_notice = next(p for p in units if p.country == "UAE" and p.normative and p.doc_type == "policy")
    pieces = [
        RetrievedPiece(piece_id=india_notice.piece_id, clause_id=india_notice.clause_id, text=india_notice.text, fused_score=1.0, rerank_score=1.0, unit=india_notice),
        RetrievedPiece(piece_id=uae_notice.piece_id, clause_id=uae_notice.clause_id, text=uae_notice.text, fused_score=1.0, rerank_score=1.0, unit=uae_notice),
    ]
    missing = detect_missing_facts(pieces, [], query_country=None)
    response = build_clarification("how many days notice do I need to give", pieces, [], missing)

    assert len(response.conditional_answers) == 2
    conditions = {ca.condition for ca in response.conditional_answers}
    assert conditions == {"if country = India", "if country = UAE"}
    for ca in response.conditional_answers:
        assert ca.answer.text  # each branch actually produced text
        assert ca.answer.citations
