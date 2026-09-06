"""Provider adapters for dense and sparse retrieval vectors."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Protocol, Self, cast, runtime_checkable

from fastembed import SparseTextEmbedding
from openai import AsyncOpenAI
from pydantic import model_validator

from hr_policy_rag.domain.models import ContractModel, NonEmptyString


class SparseEmbedding(ContractModel):
    indices: tuple[int, ...]
    values: tuple[float, ...]

    @model_validator(mode="after")
    def validate_vector(self) -> Self:
        if not self.indices or len(self.indices) != len(self.values):
            raise ValueError("sparse indices and values must have equal non-zero lengths")
        if any(index < 0 for index in self.indices):
            raise ValueError("sparse indices must be non-negative")
        if len(set(self.indices)) != len(self.indices):
            raise ValueError("sparse indices must be unique")
        return self


@runtime_checkable
class DenseEncoder(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def encode(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]: ...


@runtime_checkable
class SparseEncoder(Protocol):
    @property
    def model_name(self) -> str: ...

    async def encode(self, texts: Sequence[str]) -> tuple[SparseEmbedding, ...]: ...


class OpenAIDenseEncoder:
    """Thin, batch-preserving OpenAI embedding adapter."""

    def __init__(
        self,
        client: AsyncOpenAI,
        *,
        model_name: NonEmptyString = "text-embedding-3-small",
        dimensions: int = 1_536,
    ) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._client = client
        self._model_name = str(model_name)
        self._dimensions = dimensions
        self._total_tokens = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    async def encode(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("embedding input must contain non-empty text")
        response = await self._client.embeddings.create(
            input=list(texts),
            model=self._model_name,
            dimensions=self._dimensions,
            encoding_format="float",
        )
        self._total_tokens += response.usage.prompt_tokens
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = tuple(tuple(item.embedding) for item in ordered)
        if len(vectors) != len(texts) or any(len(vector) != self._dimensions for vector in vectors):
            raise ValueError("embedding provider returned an invalid batch")
        return vectors


class FastEmbedBm25Encoder:
    """Qdrant-supported BM25 sparse encoder, evaluated off the event loop."""

    def __init__(self, model_name: str = "Qdrant/bm25") -> None:
        self._model_name = model_name
        self._model: SparseTextEmbedding | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _encode_sync(self, texts: Sequence[str]) -> tuple[SparseEmbedding, ...]:
        if self._model is None:
            self._model = SparseTextEmbedding(self._model_name)
        raw_vectors = self._model.embed(list(texts))
        return tuple(
            SparseEmbedding(
                indices=tuple(cast(Sequence[int], vector.indices)),
                values=tuple(cast(Sequence[float], vector.values)),
            )
            for vector in raw_vectors
        )

    async def encode(self, texts: Sequence[str]) -> tuple[SparseEmbedding, ...]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("embedding input must contain non-empty text")
        return await asyncio.to_thread(self._encode_sync, texts)
