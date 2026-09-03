"""T-2.3 tests: the clause-aware chunker."""

from __future__ import annotations

from pathlib import Path

from ingestion.chunker import chunk_clause, chunk_corpus
from ingestion.parser import parse_corpus, parse_file
from ingestion.schema import Chunk, ChunkMetadata

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def _make_chunk(body: str, clause_id: str = "TEST-1") -> Chunk:
    metadata = ChunkMetadata.model_validate(
        {
            "clause_id": clause_id,
            "country": "India",
            "doc_type": "policy",
            "effective_date": "2024-01-01",
            "temporal_applicability": "POINT_IN_TIME",
        }
    )
    return Chunk(metadata=metadata, body=body, source_file="synthetic", order_in_file=0)


def test_short_clause_is_a_single_piece():
    chunk = _make_chunk("A short rule that fits in one piece easily.")
    pieces = chunk_clause(chunk)
    assert len(pieces) == 1
    assert pieces[0].piece_id == "TEST-1"
    assert pieces[0].total_pieces == 1


def test_all_real_corpus_clauses_currently_fit_in_one_piece():
    # Documents the measured fact from 3 Sep 2026: nothing in the real
    # corpus is long enough to trigger a split at the default threshold.
    # This test existing (and passing) is the evidence for that claim,
    # not an assumption baked into the chunker's design.
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    for c in chunks:
        if c.metadata.chunk_stream.value == "table":
            continue
        pieces = chunk_clause(c)
        assert len(pieces) == 1, f"{c.metadata.clause_id} unexpectedly split into {len(pieces)} pieces"


def test_long_clause_splits_but_never_between_rule_and_proviso():
    filler = "This is filler prose to pad the clause out well past the split threshold. " * 8
    body = (
        f"{filler}The employee is entitled to fifteen days wages for each year of service. "
        "Provided that where the termination is by reason of riotous or disorderly conduct "
        "the gratuity payable shall be wholly or partially forfeited, and provided further "
        "that no such forfeiture shall exceed the amount of damage caused."
    )
    chunk = _make_chunk(body)
    pieces = chunk_clause(chunk, max_chars=200)

    assert len(pieces) > 1, "test fixture should actually exercise splitting"

    # Find the piece containing the base rule sentence.
    rule_piece = next(p for p in pieces if "fifteen days wages" in p.text)
    assert "riotous or disorderly conduct" in rule_piece.text, (
        "the proviso must stay in the same piece as the rule it qualifies"
    )
    assert "provided further" in rule_piece.text.lower(), (
        "a chained second proviso must stay attached too, not just the first one"
    )


def test_oversized_atomic_group_is_kept_whole_not_cut():
    single_giant_sentence = "X " * 500 + "is a single sentence with no proviso and no split point."
    chunk = _make_chunk(single_giant_sentence)
    pieces = chunk_clause(chunk, max_chars=50)
    assert len(pieces) == 1
    assert len(pieces[0].text) > 50  # correctly oversized rather than corrupted by a mid-sentence cut


def test_table_stream_clause_rejected_by_chunk_clause():
    chunks = parse_file(
        CORPUS_DIR / "tier2_policy" / "uae" / "meridian_uae_policy.md",
        repo_root=REPO_ROOT,
    )
    housing = next(c for c in chunks if c.metadata.clause_id == "MER-AE-HOUSING-TABLE")
    try:
        chunk_clause(housing)
        assert False, "chunk_clause() should refuse a table-stream clause"
    except ValueError as e:
        assert "table_serializer" in str(e)


def test_chunk_corpus_skips_table_clauses():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    pieces = chunk_corpus(chunks)
    assert not any(p.clause_id == "MER-AE-HOUSING-TABLE" for p in pieces)
