"""
Tests for ingestion/formats/ -- the non-markdown parsers, run against REAL
generated PDF/DOCX/XLSX/CSV files (scripts/generate_multiformat_samples.py),
not synthetic text pretending to be one. This is the direct answer to
"in reality we get PDFs, Word docs, Excel, CSV, not clean markdown" --
raised 3 Sep 2026. A small representative slice, not a full corpus
rewrite: what these tests prove is that the parser layer produces the
same validated ChunkMetadata/Chunk shape regardless of source format, not
that every one of the 72 scored clauses exists in every format (it
doesn't, and duplicating them all would be busywork, not a stronger
engineering claim).

These sample files/manifests live under corpus_samples/multi_format/, not
corpus/ -- coverage_audit.py and the scored 43-probe set never see them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.formats.docx_parser import parse_docx
from ingestion.formats.pdf_parser import parse_pdf
from ingestion.formats.spreadsheet_parser import parse_csv, parse_xlsx
from ingestion.schema import ChunkMetadata

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "corpus_samples" / "multi_format"


# --- PDF ---------------------------------------------------------------

def test_pdf_parses_three_clauses_with_correct_text():
    chunks = parse_pdf(
        SAMPLES / "pdf" / "india_gratuity_law.pdf",
        SAMPLES / "pdf" / "india_gratuity_law.manifest.json",
        repo_root=REPO_ROOT,
    )
    assert len(chunks) == 3
    ceiling = next(c for c in chunks if c.metadata.clause_id == "FMT-PDF-IN-GRAT-S4-CEILING")
    assert "20,00,000" in ceiling.body
    assert "29 March 2018" in ceiling.body


def test_pdf_chunks_validate_against_real_chunk_metadata_schema():
    chunks = parse_pdf(
        SAMPLES / "pdf" / "india_gratuity_law.pdf",
        SAMPLES / "pdf" / "india_gratuity_law.manifest.json",
        repo_root=REPO_ROOT,
    )
    for c in chunks:
        # Round-trips through the SAME pydantic model the markdown parser
        # uses -- proves the pipeline is format-agnostic downstream of
        # this parser, not a parallel schema that happens to look similar.
        assert isinstance(c.metadata, ChunkMetadata)
        assert c.metadata.temporal_applicability is not None


def test_pdf_out_of_range_locator_raises(tmp_path):
    import json
    bad_manifest = tmp_path / "bad.manifest.json"
    bad_manifest.write_text(json.dumps([
        {
            "clause_id": "X",
            "locator": {"page_start": 99, "page_end": 99},
            "country": "India", "doc_type": "law",
            "effective_date": "2020-01-01", "temporal_applicability": "POINT_IN_TIME",
        }
    ]))
    with pytest.raises(ValueError):
        parse_pdf(SAMPLES / "pdf" / "india_gratuity_law.pdf", bad_manifest, repo_root=REPO_ROOT)


# --- DOCX ----------------------------------------------------------------

def test_docx_parses_two_clauses_with_correct_text():
    chunks = parse_docx(
        SAMPLES / "docx" / "meridian_india_notice.docx",
        SAMPLES / "docx" / "meridian_india_notice.manifest.json",
        repo_root=REPO_ROOT,
    )
    assert len(chunks) == 2
    junior = next(c for c in chunks if c.metadata.clause_id == "FMT-DOCX-MER-IN-NOTICE-JUNIOR")
    assert "fifteen (15) days" in junior.body
    senior = next(c for c in chunks if c.metadata.clause_id == "FMT-DOCX-MER-IN-NOTICE-SENIOR")
    assert "forty-five (45) days" in senior.body


def test_docx_chunks_validate_against_real_chunk_metadata_schema():
    chunks = parse_docx(
        SAMPLES / "docx" / "meridian_india_notice.docx",
        SAMPLES / "docx" / "meridian_india_notice.manifest.json",
        repo_root=REPO_ROOT,
    )
    for c in chunks:
        assert isinstance(c.metadata, ChunkMetadata)
        assert c.metadata.doc_type.value == "policy"


# --- XLSX ------------------------------------------------------------------

def test_xlsx_parses_thirteen_rows_matching_the_markdown_table():
    pieces = parse_xlsx(
        SAMPLES / "xlsx" / "meridian_uae_housing.xlsx",
        SAMPLES / "xlsx" / "meridian_uae_housing.manifest.json",
        repo_root=REPO_ROOT,
    )
    assert len(pieces) == 13
    m2_row = next(p for p in pieces if "M2" in p.text and "3 to 5 years" in p.text)
    assert "9500" in m2_row.text.replace(",", "") or "9,500" in m2_row.text


def test_xlsx_row_metadata_fields_present():
    pieces = parse_xlsx(
        SAMPLES / "xlsx" / "meridian_uae_housing.xlsx",
        SAMPLES / "xlsx" / "meridian_uae_housing.manifest.json",
        repo_root=REPO_ROOT,
    )
    assert all(p.metadata_fields["country"] == "UAE" for p in pieces)
    assert all(p.metadata_fields["temporal_applicability"] == "POINT_IN_TIME" for p in pieces)


# --- CSV -------------------------------------------------------------------

def test_csv_parses_same_thirteen_rows_as_xlsx():
    pieces = parse_csv(
        SAMPLES / "csv" / "meridian_uae_housing.csv",
        SAMPLES / "csv" / "meridian_uae_housing.manifest.json",
        repo_root=REPO_ROOT,
    )
    assert len(pieces) == 13
    d1_row = next(p for p in pieces if "D1" in p.text)
    assert "18000" in d1_row.text.replace(",", "") or "18,000" in d1_row.text


def test_csv_and_xlsx_produce_the_same_row_count_and_amounts():
    # The concrete proof that sharing the row-parsing code between XLSX
    # and CSV actually keeps them in sync, rather than two implementations
    # that happen to agree today.
    xlsx_pieces = parse_xlsx(
        SAMPLES / "xlsx" / "meridian_uae_housing.xlsx",
        SAMPLES / "xlsx" / "meridian_uae_housing.manifest.json",
        repo_root=REPO_ROOT,
    )
    csv_pieces = parse_csv(
        SAMPLES / "csv" / "meridian_uae_housing.csv",
        SAMPLES / "csv" / "meridian_uae_housing.manifest.json",
        repo_root=REPO_ROOT,
    )
    assert len(xlsx_pieces) == len(csv_pieces)

    def amounts(pieces):
        import re
        return sorted(int(m.replace(",", "")) for p in pieces for m in re.findall(r"[\d,]{4,}", p.text))

    assert amounts(xlsx_pieces) == amounts(csv_pieces)
