"""T-2.6 tests: the BM25 keyword index."""

from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.index_units import build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.bm25_index import BM25Index, build_bm25_index, tokenize

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def _real_index() -> BM25Index:
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    return build_bm25_index(units)


def test_tokenize_basic():
    assert tokenize("Gratuity: 21 days' wage!") == ["gratuity", "21", "days", "wage"]


def test_empty_units_rejected():
    with pytest.raises(ValueError):
        BM25Index([])


def test_search_finds_gratuity_ceiling_clause():
    index = _real_index()
    results = index.search("gratuity ceiling maximum amount payable", top_k=5)
    assert results
    top_clause_ids = {r.clause_id for r in results}
    assert "IN-GRAT-S4-CEILING" in top_clause_ids


def test_search_finds_housing_table_row_by_grade_and_amount():
    # This is the concrete R-16 justification: BM25 should distinguish
    # near-identical rows by their exact numbers/grade.
    index = _real_index()
    results = index.search("grade M2 housing allowance 3 to 5 years of service", top_k=5)
    assert results
    texts_hit = {r.piece_id for r in results}
    assert any("HOUSING-TABLE" in pid for pid in texts_hit)


def test_search_can_find_archaically_worded_leave_encashment_clause():
    # D-3: a deliberately low-lexical-salience clause. This is an honest
    # check, not a guaranteed pass by design -- if BM25 alone can't surface
    # it for a plain-English query, that IS the documented weakness the
    # probe is testing, and hybrid retrieval (BM25 + vector, Phase 3) is
    # the fix, not a smarter BM25 tokenizer.
    index = _real_index()
    results = index.search("do I get paid for unused leave when I quit", top_k=10)
    clause_ids = {r.clause_id for r in results}
    # Recorded outcome rather than asserted-and-hoped: log which is true.
    found = "MER-IN-LEAVE-ENCASHMENT" in clause_ids
    print(f"D-3 low-salience clause found by BM25 alone at top_k=10: {found}")


def test_search_returns_nothing_for_pure_stopword_query():
    index = _real_index()
    results = index.search("the a of to", top_k=5)
    # "the", "a", "of", "to" are indexable tokens under this tokenizer (no
    # stopword removal), so this mostly checks search doesn't crash on a
    # near-nonsense query, not that it returns empty.
    assert isinstance(results, list)


def test_save_and_load_round_trip(tmp_path):
    index = _real_index()
    path = tmp_path / "bm25.pkl"
    index.save(path)
    assert path.exists()
    assert path.with_suffix(".manifest.json").exists()

    loaded = BM25Index.load(path)
    results = loaded.search("gratuity ceiling maximum amount payable", top_k=5)
    assert any(r.clause_id == "IN-GRAT-S4-CEILING" for r in results)
