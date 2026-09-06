"""Deterministic, provenance-preserving ingestion."""

from hr_policy_rag.ingestion.builder import (
    build_ingestion_bundle,
    render_chunks_jsonl,
    render_ingestion_manifest,
)
from hr_policy_rag.ingestion.models import (
    ChunkingConfig,
    IngestionArtifactManifest,
    IngestionBundle,
    IngestionChunk,
    SourceIngestionSummary,
)
from hr_policy_rag.ingestion.parsers import IngestionError

__all__ = [
    "ChunkingConfig",
    "IngestionArtifactManifest",
    "IngestionBundle",
    "IngestionChunk",
    "IngestionError",
    "SourceIngestionSummary",
    "build_ingestion_bundle",
    "render_chunks_jsonl",
    "render_ingestion_manifest",
]
