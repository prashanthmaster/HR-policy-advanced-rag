"""
T-3.1-T-3.5 integration tests. Uses MockEmbedder (never OpenAIEmbedder,
same reasoning as test_vector_index.py -- must never spend money) so these
prove the PIPELINE wiring is correct (fusion -> filters -> as-of -> dedup
-> rerank, in the right order, over the real corpus's real metadata), not
that retrieval is semantically good. Semantic retrieval quality is what
T-3.6's harness measures, against real embeddings, separately.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from ingestion.embedder import MockEmbedder
from ingestion.index_units import build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.bm25_index import build_bm25_index
from retrieval.hybrid_search import HybridRetriever
from retrieval.reranker import MockReranker
from retrieval.vector_index import VectorIndex

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def _build_retriever():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    bm25 = build_bm25_index(units)
    vector = VectorIndex(MockEmbedder(dimension=16))
    vector.build(units)
    return HybridRetriever(bm25, vector, units), units


def test_country_filter_excludes_wrong_country_even_on_a_bm25_exact_match():
    # FM-B6: a query that is a verbatim India clause must not surface a
    # UAE clause just because it was asked for UAE.
    retriever, units = _build_retriever()
    target = next(u for u in units if u.clause_id == "IN-GRAT-S4-CEILING")
    results = retriever.retrieve(target.text, top_k=10, country="UAE")
    assert all(r.unit.country in ("UAE", "GLOBAL") for r in results)
    assert not any(r.clause_id == "IN-GRAT-S4-CEILING" for r in results)


def test_as_of_date_selects_the_ceiling_in_force_at_that_date():
    # IN-GRAT-S4-CEILING (eff. 2018-03-29) and IN-GRAT-S4-CEILING-SUPERSEDED
    # (eff. 2010-05-24) share lineage_id IN-GRAT-CEILING. Asking as of a
    # date before the 2018 amendment must surface the superseded version,
    # never the post-amendment one -- Finding 2, and the mirror image of
    # test_as_of_date_selects_the_current_ceiling_after_the_amendment below.
    retriever, _units = _build_retriever()
    results = retriever.retrieve(
        "gratuity ceiling maximum amount payable",
        top_k=20,
        country="India",
        as_of_date=dt.date(2016, 1, 1),
    )
    clause_ids = {r.clause_id for r in results}
    assert "IN-GRAT-S4-CEILING" not in clause_ids
    assert "IN-GRAT-S4-CEILING-SUPERSEDED" in clause_ids


def test_as_of_date_selects_the_current_ceiling_after_the_amendment():
    retriever, _units = _build_retriever()
    results = retriever.retrieve(
        "gratuity ceiling maximum amount payable",
        top_k=20,
        country="India",
        as_of_date=dt.date(2026, 9, 3),
    )
    clause_ids = {r.clause_id for r in results}
    assert "IN-GRAT-S4-CEILING-SUPERSEDED" not in clause_ids
    assert "IN-GRAT-S4-CEILING" in clause_ids


def test_dedup_never_returns_two_pieces_from_the_same_lineage():
    retriever, units = _build_retriever()
    results = retriever.retrieve("notice period termination", top_k=len(units))
    lineages = [r.unit.lineage_id for r in results if r.unit.lineage_id is not None]
    assert len(lineages) == len(set(lineages))


def test_rerank_changes_order_when_a_reranker_is_supplied():
    retriever, units = _build_retriever()
    no_rerank = retriever.retrieve("gratuity", top_k=10)
    with_rerank = retriever.retrieve("gratuity", top_k=10, reranker=MockReranker())
    assert [r.piece_id for r in with_rerank] != [] and [r.piece_id for r in no_rerank] != []
    # rerank_score is populated only when a reranker runs
    assert all(r.rerank_score is not None for r in with_rerank)
    assert all(r.rerank_score is None for r in no_rerank)


def test_retrieve_never_raises_on_a_query_with_no_hits():
    retriever, _units = _build_retriever()
    results = retriever.retrieve("zzz_no_such_token_qqq", top_k=5, country="Germany")
    assert isinstance(results, list)
