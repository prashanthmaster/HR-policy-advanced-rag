from __future__ import annotations

from pathlib import Path

import pytest

from generation.citations import build_citation, build_citations
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


def test_build_citation_pulls_the_right_fields(units):
    piece = _piece_for(units, "IN-GRAT-S4-CEILING")
    citation = build_citation(piece)
    assert citation.section == "Section 4(3), as notified"
    assert "Payment of Gratuity Act" in citation.doc
    assert citation.effective_date.isoformat() == "2018-03-29"


def test_build_citations_excludes_non_normative_pieces(units):
    illustration = _piece_for(units, "MER-IN-GRATUITY-ILLUSTRATION")
    assert illustration.unit.normative is False
    citations = build_citations([illustration])
    assert citations == []


def test_build_citations_dedupes_by_clause_id(units):
    piece = _piece_for(units, "IN-GRAT-S4-CEILING")
    citations = build_citations([piece, piece])
    assert len(citations) == 1