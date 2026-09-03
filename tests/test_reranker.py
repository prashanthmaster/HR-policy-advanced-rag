from retrieval.reranker import MockReranker


def test_mock_reranker_ranks_lexical_overlap_above_no_overlap():
    reranker = MockReranker()
    candidates = [
        ("off_topic", "the office serves coffee every morning"),
        ("on_topic", "gratuity ceiling amendment notice period"),
    ]
    ranked = reranker.rerank("gratuity ceiling amendment", candidates)
    assert ranked[0][0] == "on_topic"
    assert ranked[0][1] > ranked[1][1]


def test_mock_reranker_returns_one_score_per_candidate():
    reranker = MockReranker()
    candidates = [("a", "foo"), ("b", "bar"), ("c", "baz")]
    ranked = reranker.rerank("foo bar baz", candidates)
    assert {pid for pid, _ in ranked} == {"a", "b", "c"}


def test_mock_reranker_empty_candidates():
    assert MockReranker().rerank("anything", []) == []
