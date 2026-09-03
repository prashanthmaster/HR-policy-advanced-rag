"""T-2.7 mechanics tests: the Qdrant vector index wrapper.

Uses MockEmbedder exclusively -- never OpenAIEmbedder -- so this test file
can never spend money. These tests check that the Qdrant plumbing (build,
upsert, search, payload round-trip, idempotent point ids) works, NOT that
retrieval is semantically good -- MockEmbedder's vectors carry no real
meaning, so a query "finding" a clause here only proves the index mechanism
works, not that real embeddings will find the right clause. Semantic
retrieval quality is Phase 3/5's job, measured against real embeddings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.embedder import MockEmbedder
from ingestion.index_units import build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.vector_index import VectorIndex

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def test_build_requires_at_least_one_unit():
    index = VectorIndex(MockEmbedder())
    with pytest.raises(ValueError):
        index.build([])


def test_search_before_build_raises():
    index = VectorIndex(MockEmbedder())
    with pytest.raises(RuntimeError):
        index.search("anything")


def test_exact_text_match_ranks_first():
    # With MockEmbedder, identical text -> identical vector -> a query
    # equal to a unit's own text should retrieve that unit as the top hit
    # (cosine similarity 1.0 against itself). This exercises the upsert/
    # search/payload round trip, not semantic quality.
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    index = VectorIndex(MockEmbedder(dimension=16))
    index.build(units)

    target = next(u for u in units if u.clause_id == "IN-GRAT-S4-CEILING")
    results = index.search(target.text, top_k=3)
    assert results
    assert results[0]["clause_id"] == "IN-GRAT-S4-CEILING"


def test_build_covers_all_units():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    index = VectorIndex(MockEmbedder(dimension=8))
    index.build(units)
    # Retrieve a broad top_k and confirm the housing-table rows (a
    # non-obvious inclusion -- table pieces, not just prose clauses) made
    # it into the index at all.
    all_hits = index.search(units[0].text, top_k=len(units))
    hit_clause_ids = {r["clause_id"] for r in all_hits}
    assert "MER-AE-HOUSING-TABLE" in hit_clause_ids


def test_open_existing_reopens_a_persisted_collection_without_rebuilding(tmp_path):
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)[:3]
    path = tmp_path / "idx"

    builder = VectorIndex(MockEmbedder(dimension=8), path=path)
    builder.build(units)
    builder._client.close()  # local on-disk Qdrant single-locks the storage folder;
    # release it first, exactly as the real workflow does across two separate
    # process invocations (build_vector_index.py, then run_retrieval_harness.py).

    reopened = VectorIndex(MockEmbedder(dimension=8), path=path)
    reopened.open_existing()
    results = reopened.search(units[0].text, top_k=1)
    assert results and results[0]["clause_id"] == units[0].clause_id


def test_open_existing_without_a_prior_build_raises():
    index = VectorIndex(MockEmbedder(dimension=8))
    with pytest.raises(RuntimeError):
        index.open_existing()
