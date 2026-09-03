"""
T-2.7: vector index build (Qdrant).

This is the first module in the project that can spend OpenAI credit --
but only if constructed with an OpenAIEmbedder. Every test in this repo
uses ingestion.embedder.MockEmbedder instead, so `pytest` can never spend
money by accident; a real build is a deliberate, explicit script action
(scripts/build_vector_index.py, run by hand, not by CI or by this test
suite).

Local Qdrant only (no server, no separate deployment cost) -- either
in-memory (":memory:", for tests) or a local on-disk path (persists
between runs, so re-embedding is never needed just to search again).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ingestion.embedder import Embedder
from ingestion.index_units import IndexableUnit
from ingestion.logging_setup import get_logger

_log = get_logger("retrieval.vector_index")

_COLLECTION = "hrpolicy_clauses"


def _point_id(piece_id: str) -> int:
    # Qdrant point ids must be int or UUID, not our string piece_ids -- a
    # stable hash-derived int keeps upserts idempotent (same piece_id
    # always maps to the same point, so re-running a build overwrites
    # rather than duplicates).
    return int(hashlib.sha256(piece_id.encode("utf-8")).hexdigest()[:15], 16)


class VectorIndex:
    def __init__(self, embedder: Embedder, path: str | Path | None = None):
        self._embedder = embedder
        # location= is for remote-server URLs; a local on-disk path must go
        # through path= instead -- location= tries to urlparse the string and,
        # on Windows, misreads the drive letter ('C:\\...') as a URL scheme
        # ("Unknown scheme: c"). Found live 3 Sep 2026 on the first real
        # --live run (tests and --dry-run only ever exercised :memory:).
        if path is None:
            self._client = QdrantClient(location=":memory:")
        else:
            self._client = QdrantClient(path=str(path))

        self._built = False

    def build(self, units: list[IndexableUnit]) -> None:
        if not units:
            raise ValueError("VectorIndex.build: cannot build over zero units")

        if self._client.collection_exists(_COLLECTION):
            self._client.delete_collection(_COLLECTION)
        self._client.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=self._embedder.dimension, distance=Distance.COSINE),
        )

        vectors = self._embedder.embed([u.text for u in units])
        points = [
            PointStruct(
                id=_point_id(u.piece_id),
                vector=vec,
                payload={
                    "piece_id": u.piece_id,
                    "clause_id": u.clause_id,
                    "country": u.country,
                    "doc_type": u.doc_type,
                    "jurisdiction_scope": u.jurisdiction_scope,
                    "normative": u.normative,
                    "temporal_applicability": u.temporal_applicability,
                    "effective_date": u.effective_date.isoformat() if u.effective_date else None,
                    "effective_date_unresolved": u.effective_date_unresolved,
                    "lineage_id": u.lineage_id,
                },
            )
            for u, vec in zip(units, vectors)
        ]
        self._client.upsert(collection_name=_COLLECTION, points=points)
        self._built = True
        _log.info("built vector index over %d units", len(units))

    def open_existing(self) -> None:
        """Mark an on-disk collection built by a previous run() as ready
        to search, without re-embedding or re-upserting anything. Use
        this (not build()) when reopening build/vector_index -- build()
        deletes and recreates the collection, which would discard the
        real, already-paid-for embeddings."""
        if not self._client.collection_exists(_COLLECTION):
            raise RuntimeError(
                f"VectorIndex.open_existing: collection {_COLLECTION!r} does not exist at this path -- "
                "run scripts/build_vector_index.py --live first."
            )
        self._built = True

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if not self._built:
            raise RuntimeError("VectorIndex.search called before build()")
        query_vec = self._embedder.embed([query])[0]
        result = self._client.query_points(
            collection_name=_COLLECTION, query=query_vec, limit=top_k
        )
        return [
            {"piece_id": p.payload["piece_id"], "clause_id": p.payload["clause_id"], "score": p.score}
            for p in result.points
        ]
