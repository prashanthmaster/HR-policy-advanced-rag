"""
T-3.5: FlashRank cross-encoder rerank over the fused, filtered candidate
list.

Same pattern as ingestion/embedder.py's Embedder Protocol: a Reranker
Protocol, a real implementation, and a deterministic zero-cost/zero-network
mock that every test uses. Mirrors that module's reasoning for why the
split exists -- pytest must never depend on a model download succeeding.

Model choice: ms-marco-TinyBERT-L-2-v2, FlashRank's smallest/fastest
model. Chosen for the same reason as gpt-4o-mini and text-embedding-3-small
elsewhere in this project -- cost/speed over capability, with nothing yet
measured that would justify a larger cross-encoder. T-3.6's retrieval
harness is what could justify changing it.

Known constraint, recorded rather than worked around: FlashRank downloads
its model weights from huggingface.co on first use, and that host is
blocked by this project's sandbox network policy in BOTH the cloud
container and the device-bridge shell (the identical block hit T-2.7's
OpenAI calls -- see slot4_progress.md). The fix is the same one used
there: the one-time model download must happen from Prashanth's own
machine, in a plain terminal outside any sandbox proxy, using
scripts/build_vector_index.py's sibling script for this
(scripts/prefetch_reranker_model.py). After that one download, the cached
weights under FLASHRANK_CACHE_DIR are reused on every subsequent run --
no further network needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ingestion.logging_setup import get_logger

_log = get_logger("retrieval.reranker")

RERANK_MODEL = "ms-marco-TinyBERT-L-2-v2"
DEFAULT_CACHE_DIR = Path.home() / ".flashrank_cache"


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[tuple[str, float]]:
        """candidates: list of (piece_id, text). Returns (piece_id, score)
        pairs sorted best-first, one per input candidate."""
        ...


class FlashRankReranker:
    """Real cross-encoder reranker. Requires the model weights to already
    be cached locally (see module docstring) -- this class does not catch
    or retry a download failure; the network block should surface as a
    normal exception on the first uncached call, not be masked."""

    def __init__(self, cache_dir: Path | str | None = None, model_name: str = RERANK_MODEL):
        from flashrank import Ranker  # imported lazily, same reasoning as OpenAIEmbedder

        self._ranker = Ranker(model_name=model_name, cache_dir=str(cache_dir or DEFAULT_CACHE_DIR))

    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[tuple[str, float]]:
        from flashrank import RerankRequest

        if not candidates:
            return []
        passages = [{"id": pid, "text": text} for pid, text in candidates]
        request = RerankRequest(query=query, passages=passages)
        results = self._ranker.rerank(request)
        _log.info("reranked %d candidates for query", len(candidates))
        return [(r["id"], float(r["score"])) for r in results]


class MockReranker:
    """Deterministic, zero-cost, zero-network stand-in with the same
    interface as FlashRankReranker. Score is the count of query tokens
    (lowercased, alphanumeric-split) that also appear in the candidate
    text -- a real, if crude, lexical-overlap signal, not a hash-derived
    placeholder. This lets tests assert on actual reranking BEHAVIOUR
    (an on-topic passage should outrank an off-topic one) rather than
    only on plumbing (does rerank() return one score per candidate) --
    but it is a lexical-overlap double, not a semantic one, and no test
    should treat its exact scores as meaningful."""

    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[tuple[str, float]]:
        import re

        token_re = re.compile(r"[a-z0-9]+")
        q_tokens = set(token_re.findall(query.lower()))
        scored = []
        for pid, text in candidates:
            t_tokens = set(token_re.findall(text.lower()))
            scored.append((pid, float(len(q_tokens & t_tokens))))
        return sorted(scored, key=lambda pair: (-pair[1], pair[0]))
