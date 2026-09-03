"""
Embedding client for T-2.7, with three deliberate cost/safety controls
given the confirmed $4.98 balance:

1. EMBEDDING_MODEL is locked to text-embedding-3-small (PROJECT_PLAN.md
   Phase 2 gate note, RK-4) -- this module does not accept a caller-chosen
   model, so a future call site can't accidentally upgrade to -large.
2. EmbeddingCache: every embedded text is keyed by a hash of
   (model, text) and cached to disk. A rerun over an unchanged chunk never
   re-embeds it -- this is the "cache embeddings" mitigation the plan
   recorded for RK-4, not just a performance nicety.
3. MockEmbedder: a zero-cost, zero-network, deterministic stand-in with
   the same interface as OpenAIEmbedder. All tests use this. The real
   OpenAIEmbedder is only ever exercised by a script that requires an
   explicit --live flag (scripts/build_vector_index.py) -- pytest must
   never be able to spend money by accident.

Honesty note: this module logs how many texts were embedded and how many
came from cache. It does NOT compute or display a dollar cost -- doing
that would mean asserting a per-token price as fact without having
verified it against the account's actual current billing, which is
exactly the kind of unverified number this project's ground rule forbids.
The real cost is whatever the OpenAI dashboard says after a run; record
that observed number in PROJECT_PLAN.md's Results ledger, don't compute a
predicted one here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol

from ingestion.logging_setup import get_logger

_log = get_logger("ingestion.embedder")

EMBEDDING_MODEL = "text-embedding-3-small"


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimension(self) -> int: ...


def _cache_key(model: str, text: str) -> str:
    return hashlib.sha256(f"{model}::{text}".encode("utf-8")).hexdigest()


class EmbeddingCache:
    """A flat JSON file mapping cache_key -> vector. Loaded once, written
    once at the end of a batch (not on every single embed call) to avoid
    O(n) file rewrites over a large corpus."""

    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, list[float]] = {}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))
            _log.info("loaded embedding cache: %d entries from %s", len(self._data), path)

    def get(self, model: str, text: str) -> list[float] | None:
        return self._data.get(_cache_key(model, text))

    def put(self, model: str, text: str, vector: list[float]) -> None:
        self._data[_cache_key(model, text)] = vector

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data), encoding="utf-8")
        _log.info("saved embedding cache: %d entries to %s", len(self._data), self.path)


class OpenAIEmbedder:
    """Real embedder. Requires an OpenAI API key (via the OPENAI_API_KEY
    env var, read by the openai client itself). Every call goes through
    the cache first -- only texts not already cached hit the network."""

    def __init__(self, cache: EmbeddingCache | None = None, api_key: str | None = None):
        from openai import OpenAI  # imported lazily so importing this module never requires the package/key

        self._client = OpenAI(api_key=api_key)
        self._cache = cache
        self._dimension = 1536  # text-embedding-3-small's native output size

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float] | None] = [None] * len(texts)
        to_fetch: list[tuple[int, str]] = []

        for i, t in enumerate(texts):
            cached = self._cache.get(EMBEDDING_MODEL, t) if self._cache else None
            if cached is not None:
                results[i] = cached
            else:
                to_fetch.append((i, t))

        if to_fetch:
            _log.info(
                "embedding %d text(s) via OpenAI (%d served from cache)",
                len(to_fetch), len(texts) - len(to_fetch),
            )
            resp = self._client.embeddings.create(
                model=EMBEDDING_MODEL, input=[t for _, t in to_fetch]
            )
            for (i, t), item in zip(to_fetch, resp.data):
                results[i] = item.embedding
                if self._cache:
                    self._cache.put(EMBEDDING_MODEL, t, item.embedding)
            if self._cache:
                self._cache.save()
        else:
            _log.info("embedding %d text(s): all served from cache, no API call made", len(texts))

        return results  # type: ignore[return-value]


class MockEmbedder:
    """Deterministic, zero-cost, zero-network stand-in with the same
    interface as OpenAIEmbedder. Vectors are derived from a hash of the
    text so identical text always gets an identical (fake) vector and
    near-identical text does NOT reliably get a near-identical vector --
    this is a mechanics double, not a semantic one, and tests using it
    should only assert on exact-match / mechanical behaviour (does search
    return the point we upserted), never on retrieval quality."""

    def __init__(self, dimension: int = 8):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            vec = [(h[i % len(h)] / 255.0) * 2 - 1 for i in range(self._dimension)]
            out.append(vec)
        return out
