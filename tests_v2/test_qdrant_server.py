from __future__ import annotations

import asyncio
import datetime as dt
import os
import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from hr_policy_rag.domain import CaseFacts, PolicyTopic
from hr_policy_rag.retrieval import QdrantHybridRetriever, build_candidate_index
from tests_v2.test_qdrant_retrieval import (
    DeterministicDenseEncoder,
    DeterministicSparseEncoder,
    load_ingestion_bundle,
)

QDRANT_TEST_URL = os.getenv("QDRANT_TEST_URL")


@pytest.mark.qdrant_server
@pytest.mark.skipif(QDRANT_TEST_URL is None, reason="QDRANT_TEST_URL is set by the CI Qdrant service")
def test_pinned_qdrant_server_builds_indexes_and_executes_filtered_rrf() -> None:
    async def scenario() -> None:
        assert QDRANT_TEST_URL is not None
        collection = f"phase4_test_{uuid.uuid4().hex}"
        client = AsyncQdrantClient(url=QDRANT_TEST_URL, timeout=20)
        bundle = load_ingestion_bundle()
        dense = DeterministicDenseEncoder()
        sparse = DeterministicSparseEncoder()
        try:
            manifest = await build_candidate_index(
                client=client,
                collection_name=collection,
                artifact=bundle.manifest,
                chunks=bundle.chunks,
                dense_encoder=dense,
                sparse_encoder=sparse,
                created_at=dt.datetime(2026, 9, 6, tzinfo=dt.UTC),
            )
            info = await client.get_collection(collection)
            assert info.points_count == manifest.point_count == 126
            assert set(info.payload_schema) == {
                "corpus_generation",
                "jurisdiction",
                "topics",
                "source_id",
                "effective_from",
                "effective_to",
            }
            retriever = QdrantHybridRetriever(
                client=client,
                collection_name=collection,
                dense_encoder=dense,
                sparse_encoder=sparse,
            )
            evidence = await retriever.retrieve(
                query="confirmed UAE mainland M4 notice in August 2026",
                facts=CaseFacts(
                    country="UAE",
                    topic=PolicyTopic.NOTICE,
                    as_of_date=dt.date(2026, 8, 5),
                ),
                corpus_generation=bundle.manifest.corpus_generation,
                limit=10,
            )
            sources = {item.source_id for item in evidence}
            assert "meridian-uae-notice-policy-2026" in sources
            assert "meridian-uae-notice-policy-2022" not in sources
        finally:
            if await client.collection_exists(collection):
                await client.delete_collection(collection)
            await client.close()

    asyncio.run(scenario())
