"""Candidate-index construction and filtered dense+sparse Qdrant retrieval."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence

from qdrant_client import AsyncQdrantClient, models

from hr_policy_rag.domain import CaseFacts, Evidence, IndexManifest
from hr_policy_rag.ingestion import IngestionArtifactManifest, IngestionChunk
from hr_policy_rag.retrieval.embeddings import (
    DenseEncoder,
    EmbeddingAuthenticationError,
    EmbeddingUnavailableError,
    SparseEmbedding,
    SparseEncoder,
)

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "bm25"
_POINT_NAMESPACE = uuid.UUID("bcbad849-238d-4aab-a0a5-ecc09f311eb0")


class RetrievalError(RuntimeError):
    """Base class for typed retrieval failures."""


class IndexAlreadyExistsError(RetrievalError):
    """Candidate collection names are immutable and cannot be overwritten."""


class RetrievalContextError(RetrievalError):
    """Required deterministic retrieval facts are missing."""


class RetrievalIntegrityError(RetrievalError):
    """Qdrant returned payload that violates the requested index boundary."""


class RetrievalUnavailableError(RetrievalError):
    """Qdrant or an embedding provider was unavailable."""


def _utc_midnight(value: dt.date) -> dt.datetime:
    return dt.datetime.combine(value, dt.time(), tzinfo=dt.UTC)


def _sparse(vector: SparseEmbedding) -> models.SparseVector:
    return models.SparseVector(indices=list(vector.indices), values=list(vector.values))


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, chunk_id))


def _payload(chunk: IngestionChunk, corpus_generation: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "corpus_generation": corpus_generation,
        "text": chunk.text,
        "locator": chunk.locator,
        "jurisdiction": chunk.jurisdiction,
        "topics": list(chunk.topics),
        "normative_tier": chunk.normative_tier.value,
        "effective_from": _utc_midnight(chunk.effective_from).isoformat(),
    }
    if chunk.effective_to is not None:
        payload["effective_to"] = _utc_midnight(chunk.effective_to).isoformat()
    return payload


def _index_generation(*, ingestion_generation: str, dense_model: str, dimensions: int, sparse_model: str) -> str:
    material = json.dumps(
        {
            "ingestion_generation": ingestion_generation,
            "dense_model": dense_model,
            "dimensions": dimensions,
            "sparse_model": sparse_model,
            "fusion": "rrf",
            "schema": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()


async def build_candidate_index(
    *,
    client: AsyncQdrantClient,
    collection_name: str,
    artifact: IngestionArtifactManifest,
    chunks: Sequence[IngestionChunk],
    dense_encoder: DenseEncoder,
    sparse_encoder: SparseEncoder,
    created_at: dt.datetime,
    create_payload_indexes: bool = True,
) -> IndexManifest:
    """Build a new immutable collection; never mutate an existing candidate."""

    if len(chunks) != artifact.chunk_count:
        raise ValueError("chunk count does not match ingestion artifact")
    try:
        if await client.collection_exists(collection_name):
            raise IndexAlreadyExistsError(f"candidate collection already exists: {collection_name}")
        await client.create_collection(
            collection_name=collection_name,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size=dense_encoder.dimensions,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={SPARSE_VECTOR_NAME: models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
        if create_payload_indexes:
            for field_name in ("corpus_generation", "jurisdiction", "topics", "source_id"):
                await client.create_payload_index(
                    collection_name, field_name, models.PayloadSchemaType.KEYWORD, wait=True
                )
            for field_name in ("effective_from", "effective_to"):
                await client.create_payload_index(
                    collection_name, field_name, models.PayloadSchemaType.DATETIME, wait=True
                )

        texts = [chunk.text for chunk in chunks]
        dense_vectors, sparse_vectors = await _encode_pair(dense_encoder, sparse_encoder, texts)
        if len(dense_vectors) != len(chunks) or len(sparse_vectors) != len(chunks):
            raise RetrievalIntegrityError("encoder output count does not match chunk count")
        points = [
            models.PointStruct(
                id=_point_id(chunk.chunk_id),
                vector={DENSE_VECTOR_NAME: list(dense), SPARSE_VECTOR_NAME: _sparse(sparse)},
                payload=_payload(chunk, artifact.corpus_generation),
            )
            for chunk, dense, sparse in zip(chunks, dense_vectors, sparse_vectors, strict=True)
        ]
        await client.upsert(collection_name, points=points, wait=True)
    except (EmbeddingAuthenticationError, IndexAlreadyExistsError, RetrievalIntegrityError):
        raise
    except EmbeddingUnavailableError as exc:
        raise RetrievalUnavailableError("embedding provider unavailable during index build") from exc
    except Exception as exc:
        raise RetrievalUnavailableError("candidate index build failed") from exc

    return IndexManifest(
        index_generation=_index_generation(
            ingestion_generation=artifact.ingestion_generation,
            dense_model=dense_encoder.model_name,
            dimensions=dense_encoder.dimensions,
            sparse_model=sparse_encoder.model_name,
        ),
        corpus_generation=artifact.corpus_generation,
        corpus_sha256=artifact.corpus_sha256,
        collection_name=collection_name,
        embedding_model=dense_encoder.model_name,
        embedding_dimensions=dense_encoder.dimensions,
        sparse_model=sparse_encoder.model_name,
        point_count=len(points),
        created_at=created_at,
    )


async def _encode_pair(
    dense_encoder: DenseEncoder,
    sparse_encoder: SparseEncoder,
    texts: Sequence[str],
) -> tuple[tuple[tuple[float, ...], ...], tuple[SparseEmbedding, ...]]:
    import asyncio

    dense_task = asyncio.create_task(dense_encoder.encode(texts))
    sparse_task = asyncio.create_task(sparse_encoder.encode(texts))
    return await dense_task, await sparse_task


def _query_filter(*, facts: CaseFacts, corpus_generation: str) -> models.Filter:
    if facts.country is None or facts.topic is None or facts.as_of_date is None:
        raise RetrievalContextError("country, topic, and as_of_date are required for retrieval")
    as_of = _utc_midnight(facts.as_of_date)
    return models.Filter(
        must=[
            models.FieldCondition(key="corpus_generation", match=models.MatchValue(value=corpus_generation)),
            models.FieldCondition(key="jurisdiction", match=models.MatchAny(any=[facts.country, "GLOBAL"])),
            models.FieldCondition(key="topics", match=models.MatchValue(value=facts.topic.value)),
            models.FieldCondition(key="effective_from", range=models.DatetimeRange(lte=as_of)),
            models.Filter(
                should=[
                    models.IsEmptyCondition(is_empty=models.PayloadField(key="effective_to")),
                    models.FieldCondition(key="effective_to", range=models.DatetimeRange(gt=as_of)),
                ],
            ),
        ]
    )


class QdrantHybridRetriever:
    def __init__(
        self,
        *,
        client: AsyncQdrantClient,
        collection_name: str,
        dense_encoder: DenseEncoder,
        sparse_encoder: SparseEncoder,
        prefetch_limit: int = 30,
    ) -> None:
        if prefetch_limit <= 0:
            raise ValueError("prefetch_limit must be positive")
        self._client = client
        self._collection_name = collection_name
        self._dense_encoder = dense_encoder
        self._sparse_encoder = sparse_encoder
        self._prefetch_limit = prefetch_limit

    async def retrieve(
        self,
        *,
        query: str,
        facts: CaseFacts,
        corpus_generation: str,
        limit: int,
    ) -> Sequence[Evidence]:
        if not query.strip() or limit <= 0:
            raise RetrievalContextError("query must be non-empty and limit must be positive")
        query_filter = _query_filter(facts=facts, corpus_generation=corpus_generation)
        try:
            dense_vectors, sparse_vectors = await _encode_pair(self._dense_encoder, self._sparse_encoder, [query])
            response = await self._client.query_points(
                collection_name=self._collection_name,
                prefetch=[
                    models.Prefetch(
                        query=list(dense_vectors[0]),
                        using=DENSE_VECTOR_NAME,
                        filter=query_filter,
                        limit=self._prefetch_limit,
                    ),
                    models.Prefetch(
                        query=_sparse(sparse_vectors[0]),
                        using=SPARSE_VECTOR_NAME,
                        filter=query_filter,
                        limit=self._prefetch_limit,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        except (EmbeddingAuthenticationError, RetrievalContextError):
            raise
        except EmbeddingUnavailableError as exc:
            raise RetrievalUnavailableError("embedding provider unavailable during retrieval") from exc
        except Exception as exc:
            raise RetrievalUnavailableError("hybrid retrieval failed") from exc

        return tuple(evidence_from_payload(point.payload, point.score, corpus_generation) for point in response.points)


def evidence_from_payload(
    payload: Mapping[str, object] | None,
    score: float,
    corpus_generation: str,
) -> Evidence:
    """Validate external Qdrant payload before it enters the domain layer."""

    if payload is None or payload.get("corpus_generation") != corpus_generation:
        raise RetrievalIntegrityError("retrieval crossed the requested corpus generation")
    required = ("chunk_id", "source_id", "text", "locator")
    if any(not isinstance(payload.get(key), str) or not payload[key] for key in required):
        raise RetrievalIntegrityError("retrieval payload is incomplete")
    chunk_id = str(payload["chunk_id"])
    return Evidence(
        evidence_id=f"ev_{chunk_id}",
        chunk_id=chunk_id,
        source_id=str(payload["source_id"]),
        corpus_generation=corpus_generation,
        quote=str(payload["text"]),
        locator=str(payload["locator"]),
        retrieval_score=score,
    )
