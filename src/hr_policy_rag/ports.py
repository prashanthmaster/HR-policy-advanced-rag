"""Provider-neutral ports for the v2 application core."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Protocol, runtime_checkable

from hr_policy_rag.domain import Answer, CaseFacts, Clause, Decision, Evidence, IndexManifest, SourceDocument


@runtime_checkable
class CorpusRepository(Protocol):
    async def list_documents(self, *, status: str = "APPROVED") -> Sequence[SourceDocument]: ...  # pragma: no cover

    async def list_clauses(self, *, corpus_generation: str) -> Sequence[Clause]: ...  # pragma: no cover


@runtime_checkable
class Retriever(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        facts: CaseFacts,
        corpus_generation: str,
        limit: int,
    ) -> Sequence[Evidence]: ...  # pragma: no cover


@runtime_checkable
class AnswerModel(Protocol):
    async def generate(self, *, decision: Decision, evidence: Sequence[Evidence]) -> Answer: ...  # pragma: no cover


class GuardrailBoundary(StrEnum):
    INPUT = "INPUT"
    RETRIEVAL = "RETRIEVAL"
    OUTPUT = "OUTPUT"


class GuardrailVerdict(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    UNAVAILABLE = "UNAVAILABLE"


@runtime_checkable
class GuardrailResult(Protocol):
    @property
    def verdict(self) -> GuardrailVerdict: ...  # pragma: no cover

    @property
    def code(self) -> str: ...  # pragma: no cover


@runtime_checkable
class Guardrail(Protocol):
    async def evaluate(
        self,
        *,
        boundary: GuardrailBoundary,
        payload: object,
    ) -> GuardrailResult: ...  # pragma: no cover


@runtime_checkable
class Publisher(Protocol):
    async def publish(self, *, candidate: IndexManifest, alias: str) -> None: ...  # pragma: no cover

    async def rollback(self, *, alias: str, target_generation: str) -> None: ...  # pragma: no cover


@runtime_checkable
class Telemetry(Protocol):
    def event(
        self, *, name: str, attributes: Mapping[str, str | int | float | bool | None]
    ) -> None: ...  # pragma: no cover
