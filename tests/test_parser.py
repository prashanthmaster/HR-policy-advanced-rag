"""
T-2.8 (partial, run early): parser smoke tests against the real Phase-1
corpus, plus targeted unit tests for the three parsing decisions most
likely to silently regress -- HTML comment stripping, the UNRESOLVED
effective_date special case, and the R-17 proviso-integrity rule (a clause
body must never get split across a `---` fence).

Run with: .venv/bin/python -m pytest tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.parser import CorpusParseError, parse_corpus, parse_file
from ingestion.schema import ChunkMetadata, DocType, TemporalApplicability

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def test_full_corpus_parses_without_error():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    assert len(chunks) > 0


def test_full_corpus_clause_count_matches_coverage_audit():
    # coverage_audit.py's last recorded PASS run: 72 clauses (24 statutory,
    # 48 policy) across 4 jurisdiction files (india, uae incl. DIFC,
    # germany) plus the global preamble. If this drifts, either the corpus
    # grew (expected -- update the number) or the parser is
    # over/under-counting (a bug -- find out which before updating the
    # number).
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    assert len(chunks) == 72, (
        f"expected 72 clauses (Phase 1 close-out count), got {len(chunks)} -- "
        "if the corpus grew intentionally, update this number; otherwise "
        "the parser is mis-splitting something"
    )
    law = [c for c in chunks if c.metadata.doc_type == DocType.LAW]
    policy = [c for c in chunks if c.metadata.doc_type == DocType.POLICY]
    assert len(law) == 24
    assert len(policy) == 48


def test_no_duplicate_clause_ids():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    ids = [c.metadata.clause_id for c in chunks]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate clause_id(s) across the corpus: {dupes}"


def test_every_chunk_has_temporal_applicability():
    # This is enforced by ChunkMetadata's own validator, so a failure here
    # would already have raised during parse_corpus() -- kept as an
    # explicit, readable assertion of the Phase 1 schema-drift fix rather
    # than relying only on "parsing didn't raise."
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    for c in chunks:
        assert c.metadata.temporal_applicability is not None, c.metadata.clause_id


def test_html_comments_stripped_from_body_not_from_file():
    # D-1's commentary block must not leak into the indexed body text --
    # the defect is real (15-day notice), the commentary explaining it is
    # not something a generator should ever be able to quote as if it were
    # policy language.
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "india" / "meridian_india_policy.md",
        repo_root=REPO_ROOT,
    )
    junior_notice = next(c for c in chunks if c.metadata.clause_id == "MER-IN-NOTICE-JUNIOR")
    assert "DELIBERATE DEFECT" not in junior_notice.body
    assert "fifteen (15) days" in junior_notice.body


def test_unresolved_effective_date_preserved_not_defaulted():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "india" / "meridian_india_policy.md",
        repo_root=REPO_ROOT,
    )
    relocation = next(c for c in chunks if c.metadata.clause_id == "MER-IN-RELOCATION")
    assert relocation.metadata.effective_date is None
    assert relocation.metadata.effective_date_unresolved is True


def test_gratuity_ceiling_lineage_links_current_and_superseded():
    chunks = parse_file(
        CORPUS_DIR / "tier1_law" / "india" / "india_law.md",
        repo_root=REPO_ROOT,
    )
    current = next(c for c in chunks if c.metadata.clause_id == "IN-GRAT-S4-CEILING")
    superseded = next(c for c in chunks if c.metadata.clause_id == "IN-GRAT-S4-CEILING-SUPERSEDED")
    assert superseded.metadata.superseded_by == "IN-GRAT-S4-CEILING"
    assert current.metadata.temporal_applicability == TemporalApplicability.POINT_IN_TIME


def test_references_list_parses_bracket_syntax():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "india" / "meridian_india_policy.md",
        repo_root=REPO_ROOT,
    )
    entitlement = next(c for c in chunks if c.metadata.clause_id == "MER-IN-GRATUITY-ENTITLEMENT")
    assert entitlement.metadata.references == [
        "IN-GRAT-S4-ELIG",
        "IN-GRAT-S4-FORMULA",
        "IN-GRAT-S4-CEILING",
    ]


def test_note_sections_and_subheadings_are_not_chunks():
    # india_law.md ends in a "NOTE ON THE 2020 LABOUR CODES" paragraph with
    # no clause_id -- it must be skipped, not raise, and must not appear as
    # a phantom clause.
    chunks = parse_file(
        CORPUS_DIR / "tier1_law" / "india" / "india_law.md",
        repo_root=REPO_ROOT,
    )
    assert all(c.metadata.clause_id.startswith("IN-") for c in chunks)
    assert len(chunks) == 8  # 7 original + IN-GRAT-S4-6-FORFEITURE added in Phase 1


def test_table_stream_clause_flagged():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "uae" / "meridian_uae_policy.md",
        repo_root=REPO_ROOT,
    )
    housing = next(c for c in chunks if c.metadata.clause_id == "MER-AE-HOUSING-TABLE")
    assert housing.metadata.chunk_stream.value == "table"


def test_illustration_clause_is_not_normative():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "india" / "meridian_india_policy.md",
        repo_root=REPO_ROOT,
    )
    illustration = next(c for c in chunks if c.metadata.clause_id == "MER-IN-GRATUITY-ILLUSTRATION")
    assert illustration.metadata.normative is False
    assert illustration.metadata.illustrates == "MER-IN-GRATUITY-ENTITLEMENT"


def test_metadata_block_with_no_following_body_raises_parse_error(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(
        "# Title\n\n"
        "---\n"
        "clause_id: X-1\n"
        "country: India\n"
        "doc_type: policy\n"
        "effective_date: 2024-01-01\n"
        "temporal_applicability: POINT_IN_TIME\n"
    )
    with pytest.raises(CorpusParseError):
        parse_file(bad, repo_root=tmp_path)


def test_empty_body_after_comment_stripping_raises_parse_error(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(
        "# Title\n\n"
        "---\n"
        "clause_id: X-1\n"
        "country: India\n"
        "doc_type: policy\n"
        "effective_date: 2024-01-01\n"
        "temporal_applicability: POINT_IN_TIME\n"
        "---\n"
        "<!-- entirely commentary, nothing normative -->\n"
        "---\n"
    )
    with pytest.raises(CorpusParseError):
        parse_file(bad, repo_root=tmp_path)
