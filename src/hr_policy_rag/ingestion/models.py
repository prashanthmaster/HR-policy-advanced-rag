"""Immutable contracts for deterministic corpus ingestion artifacts."""

from __future__ import annotations

import datetime as dt
from typing import Literal, Self

from pydantic import Field, model_validator

from hr_policy_rag.corpus import SourceKind, SourceMediaType
from hr_policy_rag.domain.models import ContractModel, NonEmptyString, NormativeTier, Sha256


class ChunkingConfig(ContractModel):
    version: Literal["heading-page-v1"] = "heading-page-v1"
    max_chars: int = Field(default=1_600, ge=400, le=4_000)
    overlap_chars: int = Field(default=160, ge=0, le=500)

    @model_validator(mode="after")
    def validate_overlap(self) -> Self:
        if self.overlap_chars >= self.max_chars:
            raise ValueError("overlap_chars must be smaller than max_chars")
        return self


class IngestionChunk(ContractModel):
    schema_version: Literal[1] = 1
    chunk_id: NonEmptyString
    source_id: NonEmptyString
    source_content_sha256: Sha256
    chunk_index: int = Field(ge=0)
    text: NonEmptyString
    text_sha256: Sha256
    title: NonEmptyString
    locator: NonEmptyString
    section_path: tuple[NonEmptyString, ...]
    page_number: int | None = Field(default=None, ge=1)
    approved_locators: tuple[NonEmptyString, ...]
    document_version: NonEmptyString
    jurisdiction: NonEmptyString
    topics: tuple[NonEmptyString, ...]
    normative_tier: NormativeTier
    source_kind: SourceKind
    synthetic: bool
    published_on: dt.date
    effective_from: dt.date
    effective_to: dt.date | None = None
    supersedes: tuple[NonEmptyString, ...] = ()


class SourceIngestionSummary(ContractModel):
    source_id: NonEmptyString
    media_type: SourceMediaType
    chunk_count: int = Field(gt=0)
    extracted_characters: int = Field(gt=0)
    extracted_pages: tuple[int, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()


class IngestionArtifactManifest(ContractModel):
    schema_version: Literal[1] = 1
    corpus_generation: NonEmptyString
    corpus_sha256: Sha256
    ingestion_generation: Sha256
    chunks_sha256: Sha256
    chunking: ChunkingConfig
    parser_versions: dict[NonEmptyString, NonEmptyString]
    source_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)
    sources: tuple[SourceIngestionSummary, ...]

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.source_count != len(self.sources):
            raise ValueError("source_count must equal the number of source summaries")
        if self.chunk_count != sum(source.chunk_count for source in self.sources):
            raise ValueError("chunk_count must equal the sum of per-source chunks")
        source_ids = [source.source_id for source in self.sources]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("source summaries must have unique source IDs")
        return self


class IngestionBundle(ContractModel):
    manifest: IngestionArtifactManifest
    chunks: tuple[IngestionChunk, ...]

    @model_validator(mode="after")
    def validate_bundle(self) -> Self:
        if self.manifest.chunk_count != len(self.chunks):
            raise ValueError("manifest chunk_count must equal the number of chunks")
        chunk_ids = [chunk.chunk_id for chunk in self.chunks]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("chunk IDs must be unique")
        return self
