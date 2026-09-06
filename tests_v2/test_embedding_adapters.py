from __future__ import annotations

import asyncio
from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from openai import APIConnectionError, AsyncOpenAI, AuthenticationError
from pydantic import ValidationError

import hr_policy_rag.retrieval.embeddings as embedding_module
from hr_policy_rag.retrieval import (
    EmbeddingAuthenticationError,
    EmbeddingUnavailableError,
    FastEmbedBm25Encoder,
    OpenAIDenseEncoder,
    SparseEmbedding,
)


class FakeEmbeddingsResource:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> Any:
        self.calls.append(kwargs)
        data = [
            SimpleNamespace(index=index, embedding=vector) for index, vector in reversed(list(enumerate(self.vectors)))
        ]
        return SimpleNamespace(data=data, usage=SimpleNamespace(prompt_tokens=17))


class FakeOpenAIClient:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.embeddings = FakeEmbeddingsResource(vectors)


class FailingEmbeddingsResource:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def create(self, **kwargs: object) -> Any:
        raise self.error


class FailingOpenAIClient:
    def __init__(self, error: Exception) -> None:
        self.embeddings = FailingEmbeddingsResource(error)


def test_openai_encoder_preserves_input_order_and_requested_dimensions() -> None:
    async def scenario() -> None:
        client = FakeOpenAIClient([[1.0, 0.0], [0.0, 1.0]])
        encoder = OpenAIDenseEncoder(cast(AsyncOpenAI, client), model_name="test-model", dimensions=2)

        result = await encoder.encode(["first", "second"])

        assert result == ((1.0, 0.0), (0.0, 1.0))
        assert encoder.model_name == "test-model"
        assert encoder.dimensions == 2
        assert encoder.total_tokens == 17
        assert client.embeddings.calls == [
            {
                "input": ["first", "second"],
                "model": "test-model",
                "dimensions": 2,
                "encoding_format": "float",
            }
        ]

    asyncio.run(scenario())


def test_openai_encoder_rejects_invalid_inputs_and_provider_batches() -> None:
    with pytest.raises(ValueError, match="positive"):
        OpenAIDenseEncoder(cast(AsyncOpenAI, FakeOpenAIClient([])), dimensions=0)

    async def scenario() -> None:
        encoder = OpenAIDenseEncoder(cast(AsyncOpenAI, FakeOpenAIClient([[1.0]])), dimensions=2)
        with pytest.raises(ValueError, match="non-empty"):
            await encoder.encode([])
        with pytest.raises(ValueError, match="invalid batch"):
            await encoder.encode(["valid text"])

    asyncio.run(scenario())


def test_openai_encoder_classifies_authentication_and_availability_failures() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    authentication = AuthenticationError(
        "invalid key",
        response=httpx.Response(401, request=request),
        body={"code": "token_invalidated"},
    )
    connection = APIConnectionError(request=request)

    async def scenario() -> None:
        auth_encoder = OpenAIDenseEncoder(cast(AsyncOpenAI, FailingOpenAIClient(authentication)))
        with pytest.raises(EmbeddingAuthenticationError, match="rejected"):
            await auth_encoder.encode(["policy"])
        unavailable_encoder = OpenAIDenseEncoder(cast(AsyncOpenAI, FailingOpenAIClient(connection)))
        with pytest.raises(EmbeddingUnavailableError, match="request failed"):
            await unavailable_encoder.encode(["policy"])

    asyncio.run(scenario())


class FakeSparseVector:
    def __init__(self, indices: Sequence[int], values: Sequence[float]) -> None:
        self.indices = indices
        self.values = values


class FakeSparseModel:
    created_with: str | None = None

    def __init__(self, model_name: str) -> None:
        FakeSparseModel.created_with = model_name

    def embed(self, texts: list[str]) -> list[FakeSparseVector]:
        return [FakeSparseVector((1, 7), (1.0, float(len(text)))) for text in texts]


def test_fastembed_adapter_loads_lazily_and_returns_strict_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding_module, "SparseTextEmbedding", FakeSparseModel)

    async def scenario() -> None:
        encoder = FastEmbedBm25Encoder()
        assert encoder.model_name == "Qdrant/bm25"
        vectors = await encoder.encode(["policy", "annual leave"])
        assert vectors[0] == SparseEmbedding(indices=(1, 7), values=(1.0, 6.0))
        assert vectors[1].values == (1.0, 12.0)
        assert FakeSparseModel.created_with == "Qdrant/bm25"
        with pytest.raises(ValueError, match="non-empty"):
            await encoder.encode([" "])

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"indices": (), "values": ()},
        {"indices": (1,), "values": (1.0, 2.0)},
        {"indices": (-1,), "values": (1.0,)},
        {"indices": (1, 1), "values": (1.0, 2.0)},
    ],
)
def test_sparse_embedding_rejects_malformed_vectors(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SparseEmbedding.model_validate(kwargs)
