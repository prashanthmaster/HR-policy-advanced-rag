"""Deterministic parsing, chunking, and artifact rendering."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pypdf

from hr_policy_rag.corpus import ManifestSource, VerifiedCorpus
from hr_policy_rag.ingestion.models import (
    ChunkingConfig,
    IngestionArtifactManifest,
    IngestionBundle,
    IngestionChunk,
    SourceIngestionSummary,
)
from hr_policy_rag.ingestion.parsers import IngestionError, ParsedUnit, parse_source

MARKDOWN_PARSER_VERSION = "markdown-atx-v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_source(repository_root: Path, source: ManifestSource) -> Path:
    root = repository_root.resolve()
    path = (root / source.relative_path).resolve()
    if not path.is_relative_to(root):
        raise IngestionError("SOURCE_PATH_ESCAPE", source.source_id, source.relative_path)
    if not path.is_file():
        raise IngestionError("SOURCE_MISSING", source.source_id, source.relative_path)
    return path


def _word_windows(text: str, *, max_chars: int, overlap_chars: int) -> tuple[str, ...]:
    words = text.split()
    if not words:
        return ()
    windows: list[str] = []
    start = 0
    while start < len(words):
        end = start
        length = 0
        while end < len(words):
            next_length = length + (1 if length else 0) + len(words[end])
            if next_length > max_chars:
                break
            length = next_length
            end += 1
        if end == start:
            raise ValueError("a source contains a token longer than max_chars")
        windows.append(" ".join(words[start:end]))
        if end == len(words):
            break
        overlap_start = end
        overlap_length = 0
        while overlap_start > start:
            candidate = words[overlap_start - 1]
            candidate_length = overlap_length + (1 if overlap_length else 0) + len(candidate)
            if candidate_length > overlap_chars:
                break
            overlap_length = candidate_length
            overlap_start -= 1
        start = overlap_start if overlap_start < end else end
    return tuple(windows)


def _make_chunk(
    source: ManifestSource,
    unit: ParsedUnit,
    body: str,
    chunk_index: int,
    config: ChunkingConfig,
) -> IngestionChunk:
    context = " > ".join(unit.section_path)
    prefix = f"{context}\n\n"
    if len(prefix) >= config.max_chars:
        raise IngestionError("CHUNK_CONTEXT_TOO_LARGE", source.source_id, unit.locator)
    text = f"{prefix}{body}".strip()
    text_sha256 = _sha256(text.encode("utf-8"))
    identity = json.dumps(
        {
            "source_id": source.source_id,
            "source_content_sha256": source.content_sha256,
            "chunk_index": chunk_index,
            "locator": unit.locator,
            "text_sha256": text_sha256,
            "chunker": config.version,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    if source.title is None or source.document_version is None or source.published_on is None:
        raise IngestionError("SERVING_METADATA_MISSING", source.source_id, source.relative_path)
    if source.effective_from is None:
        raise IngestionError("SERVING_METADATA_MISSING", source.source_id, "effective_from")
    return IngestionChunk(
        chunk_id=f"chk_{_sha256(identity)[:32]}",
        source_id=source.source_id,
        source_content_sha256=source.content_sha256,
        chunk_index=chunk_index,
        text=text,
        text_sha256=text_sha256,
        title=source.title,
        locator=unit.locator,
        section_path=unit.section_path,
        page_number=unit.page_number,
        approved_locators=source.approved_locators,
        document_version=source.document_version,
        jurisdiction=source.jurisdiction,
        topics=source.topics,
        normative_tier=source.normative_tier,
        source_kind=source.source_kind,
        synthetic=source.synthetic,
        published_on=source.published_on,
        effective_from=source.effective_from,
        effective_to=source.effective_to,
        supersedes=source.supersedes,
    )


def _chunks_for_source(
    source: ManifestSource,
    units: tuple[ParsedUnit, ...],
    config: ChunkingConfig,
) -> tuple[IngestionChunk, ...]:
    chunks: list[IngestionChunk] = []
    for unit in units:
        context_size = len(" > ".join(unit.section_path)) + 2
        try:
            bodies = _word_windows(
                unit.text,
                max_chars=config.max_chars - context_size,
                overlap_chars=config.overlap_chars,
            )
        except ValueError as exc:
            raise IngestionError("CHUNK_TOKEN_TOO_LARGE", source.source_id, unit.locator) from exc
        for body in bodies:
            chunks.append(_make_chunk(source, unit, body, len(chunks), config))
    if not chunks:
        raise IngestionError("SOURCE_PRODUCED_NO_CHUNKS", source.source_id, source.relative_path)
    return tuple(chunks)


def _json_line(chunk: IngestionChunk) -> str:
    return json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def render_chunks_jsonl(chunks: tuple[IngestionChunk, ...]) -> str:
    return "".join(f"{_json_line(chunk)}\n" for chunk in chunks)


def render_ingestion_manifest(manifest: IngestionArtifactManifest) -> str:
    return json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def build_ingestion_bundle(
    corpus: VerifiedCorpus,
    *,
    repository_root: Path,
    config: ChunkingConfig | None = None,
) -> IngestionBundle:
    chunking = config or ChunkingConfig()
    all_chunks: list[IngestionChunk] = []
    summaries: list[SourceIngestionSummary] = []

    for source in sorted(corpus.serving_sources, key=lambda item: item.source_id):
        path = _resolve_source(repository_root, source)
        parsed = parse_source(source, path)
        chunks = _chunks_for_source(source, parsed.units, chunking)
        all_chunks.extend(chunks)
        summaries.append(
            SourceIngestionSummary(
                source_id=source.source_id,
                media_type=source.media_type,
                chunk_count=len(chunks),
                extracted_characters=sum(len(unit.text) for unit in parsed.units),
                extracted_pages=tuple(unit.page_number for unit in parsed.units if unit.page_number is not None),
                warnings=parsed.warnings,
            )
        )

    chunk_tuple = tuple(all_chunks)
    chunks_jsonl = render_chunks_jsonl(chunk_tuple)
    chunks_sha256 = _sha256(chunks_jsonl.encode("utf-8"))
    parser_versions = {
        "markdown": MARKDOWN_PARSER_VERSION,
        "pdf": f"pypdf-{pypdf.__version__}-layout",
    }
    generation_identity = json.dumps(
        {
            "corpus_sha256": corpus.corpus_sha256,
            "chunks_sha256": chunks_sha256,
            "chunking": chunking.model_dump(mode="json"),
            "parser_versions": parser_versions,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    manifest = IngestionArtifactManifest(
        corpus_generation=corpus.manifest.corpus_generation,
        corpus_sha256=corpus.corpus_sha256,
        ingestion_generation=_sha256(generation_identity),
        chunks_sha256=chunks_sha256,
        chunking=chunking,
        parser_versions=parser_versions,
        source_count=len(summaries),
        chunk_count=len(chunk_tuple),
        sources=tuple(summaries),
    )
    return IngestionBundle(manifest=manifest, chunks=chunk_tuple)
