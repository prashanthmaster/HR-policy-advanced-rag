"""T-2.4 tests: table serialization for chunk_stream == 'table' clauses."""

from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.parser import parse_file
from ingestion.table_serializer import serialize_table_clause

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def _housing_clause():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "uae" / "meridian_uae_policy.md",
        repo_root=REPO_ROOT,
    )
    return next(c for c in chunks if c.metadata.clause_id == "MER-AE-HOUSING-TABLE")


def test_housing_table_serializes_to_thirteen_rows():
    pieces = serialize_table_clause(_housing_clause())
    assert len(pieces) == 13
    assert pieces[0].piece_id == "MER-AE-HOUSING-TABLE#row0"
    assert all(p.total_rows == 13 for p in pieces)


def test_each_row_is_self_contained_with_title_and_trailer():
    pieces = serialize_table_clause(_housing_clause())
    m2_row = next(p for p in pieces if "Grade M2, 3 to 5 years" in p.text)
    assert "9,500 per month" in m2_row.text
    assert "Schedule 2" in m2_row.text  # title carried onto every row
    assert "not part of basic wage" in m2_row.text  # trailing qualifier carried onto every row


def test_specific_cell_value_is_correct():
    pieces = serialize_table_clause(_housing_clause())
    d1_row = next(p for p in pieces if "Grade D1" in p.text)
    assert "18,000 per month" in d1_row.text


def test_non_table_clause_rejected():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "uae" / "meridian_uae_policy.md",
        repo_root=REPO_ROOT,
    )
    non_table = next(c for c in chunks if c.metadata.clause_id != "MER-AE-HOUSING-TABLE")
    with pytest.raises(ValueError):
        serialize_table_clause(non_table)
