from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import math
import re
from collections.abc import Sequence
from pathlib import Path

import pytest
from qdrant_client import AsyncQdrantClient

from hr_policy_rag.corpus import load_verified_corpus
from hr_policy_rag.domain import CaseFacts, PolicyTopic
from hr_policy_rag.ingestion import IngestionChunk, build_ingestion_bundle
from hr_policy_rag.retrieval import (
    IndexAlreadyExistsError,
    QdrantHybridRetriever,
    RetrievalContextError,
    RetrievalIntegrityError,
    RetrievalUnavailableError,
    SparseEmbedding,
    build_candidate_index,
)
from hr_policy_rag.retrieval.qdrant_store import evidence_from_payload

ROOT = Path(__file__).resolve().parents[1]
CORPUS_MANIFEST_PATH = ROOT / "corpus_v2" / "manifest.json"


class DeterministicDenseEncoder:
    model_name = "test-dense-v1"
    dimensions = 8

    async def encode(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        groups = (
            ("gratuity", "end-of-service", "benefit"),
            ("notice", "resignation", "probation"),
            ("leave", "calendar days", "working days"),
            ("india", "meridian india"),
            ("uae", "mainland"),
            ("wage", "salary", "ctc"),
            ("carry-forward", "carry forward"),
            ("m3", "m4", "grade"),
        )
        vectors: list[tuple[float, ...]] = []
        for text in texts:
            folded = text.casefold()
            raw = [float(sum(term in folded for term in group)) for group in groups]
            norm = math.sqrt(sum(value * value for value in raw)) or 1.0
            vectors.append(tuple(value / norm for value in raw))
        return tuple(vectors)


class DeterministicSparseEncoder:
    model_name = "test-bm25-v1"

    async def encode(self, texts: Sequence[str]) -> tuple[SparseEmbedding, ...]:
        output: list[SparseEmbedding] = []
        for text in texts:
            tokens = sorted(set(re.findall(r"[a-z0-9]+", text.casefold())))
            indices = tuple(int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big") for token in tokens)
            output.append(SparseEmbedding(indices=indices, values=(1.0,) * len(indices)))
        return tuple(output)


def load_ingestion_bundle():
    corpus = load_verified_corpus(CORPUS_MANIFEST_PATH, repository_root=ROOT)
    return build_ingestion_bundle(corpus, repository_root=ROOT)


async def _built_retriever() -> tuple[AsyncQdrantClient, QdrantHybridRetriever, str]:
    bundle = load_ingestion_bundle()
    client = AsyncQdrantClient(":memory:")
    dense = DeterministicDenseEncoder()
    sparse = DeterministicSparseEncoder()
    await build_candidate_index(
        client=client,
        collection_name="candidate",
        artifact=bundle.manifest,
        chunks=bundle.chunks,
        dense_encoder=dense,
        sparse_encoder=sparse,
        created_at=dt.datetime(2026, 9, 6, tzinfo=dt.UTC),
        create_payload_indexes=False,
    )
    retriever = QdrantHybridRetriever(
        client=client,
        collection_name="candidate",
        dense_encoder=dense,
        sparse_encoder=sparse,
    )
    return client, retriever, bundle.manifest.corpus_generation


def test_candidate_index_contains_every_chunk_and_cannot_be_overwritten() -> None:
    async def scenario() -> None:
        bundle = load_ingestion_bundle()
        client = AsyncQdrantClient(":memory:")
        dense = DeterministicDenseEncoder()
        sparse = DeterministicSparseEncoder()
        manifest = await build_candidate_index(
            client=client,
            collection_name="candidate",
            artifact=bundle.manifest,
            chunks=bundle.chunks,
            dense_encoder=dense,
            sparse_encoder=sparse,
            created_at=dt.datetime(2026, 9, 6, tzinfo=dt.UTC),
            create_payload_indexes=False,
        )
        assert manifest.point_count == len(bundle.chunks) == 126
        assert manifest.corpus_generation == bundle.manifest.corpus_generation
        assert manifest.embedding_model == dense.model_name
        with pytest.raises(IndexAlreadyExistsError):
            await build_candidate_index(
                client=client,
                collection_name="candidate",
                artifact=bundle.manifest,
                chunks=bundle.chunks,
                dense_encoder=dense,
                sparse_encoder=sparse,
                created_at=dt.datetime(2026, 9, 6, tzinfo=dt.UTC),
                create_payload_indexes=False,
            )
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("as_of_date", "required_source", "forbidden_source"),
    [
        (dt.date(2026, 7, 15), "meridian-uae-notice-policy-2022", "meridian-uae-notice-policy-2026"),
        (dt.date(2026, 8, 5), "meridian-uae-notice-policy-2026", "meridian-uae-notice-policy-2022"),
    ],
)
def test_hybrid_retrieval_enforces_effective_date_boundaries(
    as_of_date: dt.date, required_source: str, forbidden_source: str
) -> None:
    async def scenario() -> None:
        client, retriever, generation = await _built_retriever()
        evidence = await retriever.retrieve(
            query="What notice applies to a confirmed UAE mainland M4 employee?",
            facts=CaseFacts(country="UAE", topic=PolicyTopic.NOTICE, as_of_date=as_of_date),
            corpus_generation=generation,
            limit=10,
        )
        source_ids = {item.source_id for item in evidence}
        assert required_source in source_ids
        assert forbidden_source not in source_ids
        assert all(item.corpus_generation == generation for item in evidence)
        await client.close()

    asyncio.run(scenario())


def test_hybrid_retrieval_enforces_jurisdiction_and_topic_filters() -> None:
    async def scenario() -> None:
        client, retriever, generation = await _built_retriever()
        evidence = await retriever.retrieve(
            query="How many working days of privilege leave are carried forward in India?",
            facts=CaseFacts(country="India", topic=PolicyTopic.LEAVE, as_of_date=dt.date(2026, 8, 1)),
            corpus_generation=generation,
            limit=10,
        )
        chunk_by_id = {chunk.chunk_id: chunk for chunk in load_ingestion_bundle().chunks}
        assert evidence
        assert all(chunk_by_id[item.chunk_id].jurisdiction in {"India", "GLOBAL"} for item in evidence)
        assert all("leave" in chunk_by_id[item.chunk_id].topics for item in evidence)
        assert all(not item.source_id.startswith("fixture-") for item in evidence)
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "facts",
    [
        CaseFacts(topic=PolicyTopic.NOTICE, as_of_date=dt.date(2026, 8, 1)),
        CaseFacts(country="UAE", as_of_date=dt.date(2026, 8, 1)),
        CaseFacts(country="UAE", topic=PolicyTopic.NOTICE),
    ],
)
def test_missing_deterministic_context_fails_before_querying(facts: CaseFacts) -> None:
    async def scenario() -> None:
        client, retriever, generation = await _built_retriever()
        with pytest.raises(RetrievalContextError, match="country, topic, and as_of_date"):
            await retriever.retrieve(
                query="notice period",
                facts=facts,
                corpus_generation=generation,
                limit=10,
            )
        await client.close()

    asyncio.run(scenario())


def test_candidate_builder_rejects_partial_ingestion_input() -> None:
    async def scenario() -> None:
        bundle = load_ingestion_bundle()
        client = AsyncQdrantClient(":memory:")
        chunks: tuple[IngestionChunk, ...] = bundle.chunks[:-1]
        with pytest.raises(ValueError, match="chunk count"):
            await build_candidate_index(
                client=client,
                collection_name="candidate",
                artifact=bundle.manifest,
                chunks=chunks,
                dense_encoder=DeterministicDenseEncoder(),
                sparse_encoder=DeterministicSparseEncoder(),
                created_at=dt.datetime(2026, 9, 6, tzinfo=dt.UTC),
                create_payload_indexes=False,
            )
        await client.close()

    asyncio.run(scenario())


def test_retriever_rejects_invalid_request_before_provider_calls() -> None:
    async def scenario() -> None:
        client, retriever, generation = await _built_retriever()
        facts = CaseFacts(country="UAE", topic=PolicyTopic.NOTICE, as_of_date=dt.date(2026, 8, 1))
        with pytest.raises(RetrievalContextError, match="non-empty"):
            await retriever.retrieve(query=" ", facts=facts, corpus_generation=generation, limit=10)
        with pytest.raises(RetrievalContextError, match="positive"):
            await retriever.retrieve(query="notice", facts=facts, corpus_generation=generation, limit=0)
        await client.close()

    asyncio.run(scenario())


def test_payload_integrity_checks_reject_generation_drift_and_missing_fields() -> None:
    with pytest.raises(RetrievalIntegrityError, match="corpus generation"):
        evidence_from_payload(None, 0.5, "generation-a")
    with pytest.raises(RetrievalIntegrityError, match="corpus generation"):
        evidence_from_payload({"corpus_generation": "generation-b"}, 0.5, "generation-a")
    with pytest.raises(RetrievalIntegrityError, match="incomplete"):
        evidence_from_payload({"corpus_generation": "generation-a"}, 0.5, "generation-a")


def test_closed_qdrant_client_becomes_typed_unavailable_error() -> None:
    async def scenario() -> None:
        client, retriever, generation = await _built_retriever()
        await client.close()
        with pytest.raises(RetrievalUnavailableError, match="hybrid retrieval failed"):
            await retriever.retrieve(
                query="notice period",
                facts=CaseFacts(
                    country="UAE",
                    topic=PolicyTopic.NOTICE,
                    as_of_date=dt.date(2026, 8, 1),
                ),
                corpus_generation=generation,
                limit=10,
            )

    asyncio.run(scenario())
