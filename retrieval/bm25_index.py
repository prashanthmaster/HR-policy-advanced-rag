"""
T-2.6: BM25 keyword index build.

No OpenAI cost -- pure lexical retrieval over rank_bm25's Okapi
implementation. Deliberately built and committed before T-2.7 (the vector
index) because it needs no API key and no budget, and because D-3's whole
point (an archaically-worded, low-lexical-salience clause) and the R-16
housing table's whole point (BM25 is what actually lands the right row,
not embeddings) both live on this leg of retrieval specifically -- it is
not a placeholder waiting on the "real" index.

Tokenizer is intentionally simple: lowercase, split on non-alphanumeric
runs, no stemming, no stopword removal. Honesty note: this has not been
tuned or measured against any retrieval metric yet (that's Phase 3's
Context Precision/Recall work) -- it is a reasonable default, not a
verified-good one.
"""

from __future__ import annotations

import json
import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from ingestion.index_units import IndexableUnit
from ingestion.logging_setup import get_logger

_log = get_logger("retrieval.bm25_index")

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class BM25SearchResult:
    piece_id: str
    clause_id: str
    score: float


class BM25Index:
    """Wraps rank_bm25.BM25Okapi with the piece_id/clause_id bookkeeping a
    raw BM25Okapi instance doesn't carry, plus save/load so a build doesn't
    have to be repeated on every process start."""

    def __init__(self, units: list[IndexableUnit]):
        if not units:
            raise ValueError("BM25Index: cannot build an index over zero units")
        self._units = units
        self._tokenized = [tokenize(u.text) for u in units]
        self._bm25 = BM25Okapi(self._tokenized)
        _log.info("built BM25 index over %d units", len(units))

    def search(self, query: str, top_k: int = 10) -> list[BM25SearchResult]:
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(range(len(self._units)), key=lambda i: scores[i], reverse=True)
        return [
            BM25SearchResult(
                piece_id=self._units[i].piece_id,
                clause_id=self._units[i].clause_id,
                score=float(scores[i]),
            )
            for i in ranked[:top_k]
            if scores[i] > 0
        ]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"units": self._units, "bm25": self._bm25}, f)
        manifest = path.with_suffix(".manifest.json")
        manifest.write_text(
            json.dumps({"unit_count": len(self._units), "clause_count": len({u.clause_id for u in self._units})}, indent=2),
            encoding="utf-8",
        )
        _log.info("saved BM25 index to %s (%d units)", path, len(self._units))

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        with open(path, "rb") as f:
            data = pickle.load(f)
        obj = cls.__new__(cls)
        obj._units = data["units"]
        obj._bm25 = data["bm25"]
        obj._tokenized = None  # not needed after load; search only needs self._bm25 and self._units
        return obj


def build_bm25_index(units: list[IndexableUnit]) -> BM25Index:
    return BM25Index(units)
