"""Tests for generation/supersession.py (T-4.6 / FM-E6), against real
corpus fixtures: IN-GRAT-S4-CEILING / IN-GRAT-S4-CEILING-SUPERSEDED for
the stale-citation warning, DIFC-L2-2019-DEWS / DIFC-EOSB-LEGACY-GRATUITY
for the legitimate no-warning split case."""

from __future__ import annotations

from pathlib import Path

import pytest

from generation.generator import TemplateGenerator
from generation.supersession import check_supersession
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


def test_citing_only_the_superseded_clause_warns(units):
    """A real staleness scenario: citing IN-GRAT-S4-CEILING-SUPERSEDED
    (superseded_by IN-GRAT-S4-CEILING) alone, without its replacement,
    must warn."""
    superseded = _piece_for(units, "IN-GRAT-S4-CEILING-SUPERSEDED")
    notes, warning = check_supersession([superseded])
    assert warning is not None
    assert "IN-GRAT-S4-CEILING-SUPERSEDED" in warning
    assert "IN-GRAT-S4-CEILING" in warning


def test_citing_both_the_superseded_clause_and_its_replacement_does_not_warn(units):
    """If the replacement IS also cited (a caller deliberately wants both
    for comparison), that's not a stale citation."""
    superseded = _piece_for(units, "IN-GRAT-S4-CEILING-SUPERSEDED")
    current = _piece_for(units, "IN-GRAT-S4-CEILING")
    notes, warning = check_supersession([superseded, current])
    assert warning is None


def test_legitimate_segmented_split_produces_an_amendment_note_not_a_warning(units):
    """P-3a's real straddle pair: both DIFC-L2-2019-DEWS and
    DIFC-EOSB-LEGACY-GRATUITY are correctly cited together per T-4.3 --
    this must produce an informational note (DEWS supersedes the legacy
    clause), never a stale-citation warning."""
    dews = _piece_for(units, "DIFC-L2-2019-DEWS")
    legacy = _piece_for(units, "DIFC-EOSB-LEGACY-GRATUITY")
    notes, warning = check_supersession([dews, legacy])
    assert warning is None
    assert any("DIFC-L2-2019-DEWS supersedes DIFC-EOSB-LEGACY-GRATUITY" in n for n in notes)


def test_no_supersession_relationship_is_silent(units):
    piece = _piece_for(units, "MER-IN-LEAVE-ANNUAL-V1")  # older side, superseded_by set but not cited alone here on its own outside a pair below
    # Isolate a clause with neither field set at all:
    plain = next(u for u in units if u.supersedes is None and u.superseded_by is None and u.normative)
    plain_piece = RetrievedPiece(piece_id=plain.piece_id, clause_id=plain.clause_id, text=plain.text, fused_score=1.0, rerank_score=1.0, unit=plain)
    notes, warning = check_supersession([plain_piece])
    assert notes == []
    assert warning is None


def test_generator_surfaces_the_warning_in_text_and_field(units):
    superseded = _piece_for(units, "IN-GRAT-S4-CEILING-SUPERSEDED")
    answer = TemplateGenerator().generate("what was the old gratuity ceiling", [superseded], [])
    assert answer.superseded_warning is not None
    assert "WARNING" in answer.text
