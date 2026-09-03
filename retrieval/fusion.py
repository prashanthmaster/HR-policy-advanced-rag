"""
T-3.1: Reciprocal Rank Fusion (RRF) over BM25 + vector search.

RRF combines two rankings by rank position alone, never by raw score --
BM25 scores and cosine-similarity scores live on incomparable scales, so
fusing them by score would silently let whichever retriever produces
larger numbers dominate. RRF sidesteps that: a piece_id's fused score is
the sum, across every ranking it appears in, of 1/(k + rank).

k=60 is the constant from the original RRF paper (Cormack, Clarke & Buettcher
2009) and is used here as a reasonable, widely-used default -- it has NOT
been tuned against this corpus. T-3.6's retrieval harness (Context
Precision/Recall over the probe set) is what could justify changing it;
until that comparison is actually run, this is a default, not a measured
choice, and must not be described as one.
"""

from __future__ import annotations

from collections import defaultdict

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = DEFAULT_RRF_K
) -> dict[str, float]:
    """rankings: one ranked list of piece_ids per retriever, best-first,
    no duplicate piece_ids within a single ranking. A piece_id missing
    from a given ranking contributes 0 from that ranking -- it is not
    penalized beyond simply not accumulating a term.

    Returns {piece_id: fused_score}, higher is better. Empty input (zero
    rankings, or rankings that are all empty) returns {}.
    """
    if k < 0:
        raise ValueError(f"reciprocal_rank_fusion: k must be >= 0, got {k}")
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, piece_id in enumerate(ranking, start=1):
            scores[piece_id] += 1.0 / (k + rank)
    return dict(scores)


def fuse_and_rank(rankings: list[list[str]], k: int = DEFAULT_RRF_K) -> list[str]:
    """Convenience wrapper: fuse, then return piece_ids sorted best-first.
    Ties broken by piece_id (stable, deterministic) rather than left to
    Python's sort-stability-on-insertion-order, which would depend on
    which ranking happened to list a tied piece_id first."""
    scores = reciprocal_rank_fusion(rankings, k=k)
    return sorted(scores, key=lambda pid: (-scores[pid], pid))
