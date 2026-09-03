from retrieval.fusion import DEFAULT_RRF_K, fuse_and_rank, reciprocal_rank_fusion


def test_agreement_across_both_rankings_beats_single_ranking_top1():
    # "b" is #1 in one ranking and #2 in the other; "a" is #1 in the other
    # ranking but absent from the first. RRF should reward the piece both
    # retrievers agree is relevant over one retriever's lone top pick.
    bm25 = ["b", "c", "d"]
    vector = ["a", "b", "e"]
    fused = fuse_and_rank([bm25, vector])
    assert fused[0] == "b"


def test_missing_from_one_ranking_still_contributes_from_the_other():
    scores = reciprocal_rank_fusion([["x"], []])
    assert scores == {"x": 1.0 / (DEFAULT_RRF_K + 1)}


def test_empty_rankings_produce_empty_scores():
    assert reciprocal_rank_fusion([]) == {}
    assert reciprocal_rank_fusion([[], []]) == {}


def test_negative_k_rejected():
    import pytest

    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], k=-1)


def test_ties_broken_deterministically_by_piece_id():
    # both pieces rank #1 in one list each -- identical fused score
    fused = fuse_and_rank([["a"], ["b"]])
    assert fused == ["a", "b"]
