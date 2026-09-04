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


# --- Session 5 fix: min_rerank_score (top_k as a ceiling, not a target) ---


def test_min_rerank_score_none_by_default_preserves_old_padding_behaviour():
    """Regression guard: the default must stay backward-compatible so
    every existing call site (grading/pipeline.py, eval scripts) keeps
    its already-tested behaviour unless it deliberately opts in."""
    retriever, units = _build_retriever()
    results = retriever.retrieve("gratuity", top_k=10, reranker=MockReranker())
    assert len(results) == 10


def test_min_rerank_score_drops_low_scoring_pieces_before_truncating():
    # MockReranker scores by exact query-token overlap count (see
    # retrieval/reranker.py) -- a query with only one on-topic token
    # scores the on-topic piece(s) >=1 and everything else 0.
    retriever, units = _build_retriever()
    target = next(u for u in units if u.clause_id == "MER-AE-HOUSING-TABLE")
    no_floor = retriever.retrieve(target.text[:40], top_k=10, reranker=MockReranker())
    floored = retriever.retrieve(target.text[:40], top_k=10, reranker=MockReranker(), min_rerank_score=1.0)
    assert len(floored) <= len(no_floor)
    assert all(r.rerank_score >= 1.0 for r in floored)
    # the floor must not silently return nothing when something real qualifies
    assert any(r.clause_id == "MER-AE-HOUSING-TABLE" for r in floored)


def test_min_rerank_score_can_legitimately_return_fewer_than_top_k():
    """top_k becomes a CEILING, not a fixed target -- this is the actual
    behaviour change the bug fix makes. A very high floor should return
    few or zero results rather than padding out with irrelevant pieces."""
    retriever, _units = _build_retriever()
    results = retriever.retrieve("gratuity", top_k=10, reranker=MockReranker(), min_rerank_score=999.0)
    assert results == []


def test_min_rerank_score_ignored_without_a_reranker():
    """Documented scope limit: fused_score is a reciprocal-rank score,
    not a calibrated relevance magnitude, so the floor only applies to
    real rerank_score values -- passing it with no reranker must not
    raise and must not change the unfloored fallback behaviour."""
    retriever, _units = _build_retriever()
    without_floor = retriever.retrieve("gratuity", top_k=10)
    with_floor_but_no_reranker = retriever.retrieve("gratuity", top_k=10, min_rerank_score=0.5)
    assert [r.piece_id for r in without_floor] == [r.piece_id for r in with_floor_but_no_reranker]
