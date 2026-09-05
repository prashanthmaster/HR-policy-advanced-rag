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
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

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
    def __init__(
        self,
        embedder: Embedder,
        path: str | Path | None = None,
        url: str | None = None,
        api_key: str | None = None,
    ):
        """Three mutually exclusive backends, checked in this order:

        1. url set (T-8.2, Qdrant Cloud) -- a real remote Qdrant instance,
           reached over HTTPS. This is the only mode that survives a Cloud
           Run deploy: Cloud Run containers have no persistent local disk
           across restarts/instances, so the on-disk path=/  :memory: modes
           below cannot serve a deployed app. api_key is required by every
           Qdrant Cloud cluster (unauthenticated remote access is not an
           option Qdrant Cloud offers).
        2. path set, url not set -- local on-disk Qdrant (dev machine only).
        3. neither set -- in-memory Qdrant (tests only).

        location= is for remote-server URLs generally, but url= is used
        here instead of routing url through location= because location=
        historically also had to double as the local on-disk path parameter
        in this codebase, and a local on-disk path must go through path=
        instead of location= -- location= tries to urlparse the string and,
        on Windows, misreads the drive letter ('C:\\...') as a URL scheme
        ("Unknown scheme: c"). Found live 3 Sep 2026 on the first real
        --live run (tests and --dry-run only ever exercised :memory:).
        Keeping url= as its own explicit parameter avoids that ambiguity
        being reintroduced now that a real remote case exists.
        """
        self._embedder = embedder
        if url is not None:
            self._client = QdrantClient(url=url, api_key=api_key)
        elif path is None:
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
                    "source_file": u.source_file,
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

    def close(self) -> None:
        """Release the on-disk Qdrant storage lock. Local on-disk Qdrant
        single-locks its storage folder, so a process holding a VectorIndex
        open against a path must close() it before ANY other VectorIndex
        (in this process or another) can open the same path -- including
        VectorIndex.reindex_source_file()'s own client inside drive_sync.
        reindex. Safe to call more than once; a fresh VectorIndex must be
        constructed to use the collection again afterward (this doesn't
        reopen)."""
        self._client.close()

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

    def reindex_source_file(self, source_file: str, units: list[IndexableUnit]) -> None:
        """T-6.4 -- incremental re-index of a single changed document.

        Unlike build(), this does NOT delete/recreate the whole collection.
        It deletes only the existing points whose payload.source_file
        matches `source_file` (so a clause removed from the source in this
        edit doesn't linger as a stale point), then embeds and upserts the
        freshly-parsed units for that file. Every other document's points
        are untouched -- both the point of "incremental" and the reason
        this project's OpenAI budget survives a Phase 6 demo: the embedder's
        own cache (ingestion/embedder.py) already means unchanged clause
        text is never re-billed even on a full rebuild, but this also
        avoids the Qdrant-side churn of wiping and rebuilding all ~84
        points to change ~1 document's worth.

        Requires the collection to already exist (via a prior build()) --
        this is deliberately update-only, not a from-scratch build path.
        """
        if not self._client.collection_exists(_COLLECTION):
            raise RuntimeError(
                f"VectorIndex.reindex_source_file: collection {_COLLECTION!r} does not exist -- "
                "run scripts/build_vector_index.py --live at least once before incremental updates."
            )

        self._client.delete(
            collection_name=_COLLECTION,
            points_selector=Filter(
                must=[FieldCondition(key="source_file", match=MatchValue(value=source_file))]
            ),
        )

        if units:
            vectors = self._embedder.embed([u.text for u in units])
            points = [
                PointStruct(
                    id=_point_id(u.piece_id),
                    vector=vec,
                    payload={
                        "piece_id": u.piece_id,
                        "clause_id": u.clause_id,
                        "source_file": u.source_file,
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
        _log.info(
            "reindexed source_file=%s: removed old points, upserted %d new unit(s)",
            source_file, len(units),
        )

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
