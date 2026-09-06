"""Versioned corpus manifest validation.

The manifest is the only route from repository files into the future serving
index. Files outside its ``SERVING`` set remain visible for audit and tests but
cannot enter production retrieval accidentally.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Literal, Self

from pydantic import HttpUrl, model_validator

from hr_policy_rag.domain.models import ContractModel, NonEmptyString, NormativeTier, Sha256

_SYNTHETIC_BANNER_MARKERS = (
    "SYNTHETIC DOCUMENT",
    "NOT A REAL COMPANY POLICY",
)


class CorpusUse(StrEnum):
    """Whether a source may enter the serving corpus."""

    SERVING = "SERVING"
    ADVERSARIAL_TEST = "ADVERSARIAL_TEST"
    QUARANTINED = "QUARANTINED"
    DEFERRED = "DEFERRED"


class CertificationLevel(StrEnum):
    """Evidence level recorded for a source review."""

    NOT_REVIEWED = "NOT_REVIEWED"
    PRIMARY_SOURCE_CHECKED = "PRIMARY_SOURCE_CHECKED"
    DEMO_POLICY_REVIEWED = "DEMO_POLICY_REVIEWED"
    LEGAL_REVIEWED = "LEGAL_REVIEWED"


class ManifestSource(ContractModel):
    source_id: NonEmptyString
    relative_path: NonEmptyString
    content_sha256: Sha256
    use: CorpusUse
    jurisdiction: NonEmptyString
    topics: tuple[NonEmptyString, ...]
    normative_tier: NormativeTier
    synthetic: bool
    certification_level: CertificationLevel
    official_source_urls: tuple[HttpUrl, ...] = ()
    reason_codes: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        relative_path = PurePosixPath(self.relative_path)
        if relative_path.is_absolute() or ".." in relative_path.parts or "\\" in self.relative_path:
            raise ValueError("relative_path must be a repository-relative POSIX path without traversal")
        if len(set(self.topics)) != len(self.topics):
            raise ValueError("topics must not contain duplicates")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")

        if self.use is not CorpusUse.SERVING:
            if not self.reason_codes:
                raise ValueError("a non-serving source requires at least one reason code")
            return self

        if self.reason_codes:
            raise ValueError("a serving source cannot carry quarantine or deferral reason codes")
        if self.normative_tier is NormativeTier.STATUTORY:
            if self.synthetic:
                raise ValueError("a serving statutory source cannot be synthetic")
            if not self.official_source_urls:
                raise ValueError("a serving statutory source requires an official source URL")
            if self.certification_level not in {
                CertificationLevel.PRIMARY_SOURCE_CHECKED,
                CertificationLevel.LEGAL_REVIEWED,
            }:
                raise ValueError("a serving statutory source requires primary-source certification")
        elif not self.synthetic:
            raise ValueError("a serving demo company policy must be explicitly synthetic")
        elif self.certification_level not in {
            CertificationLevel.DEMO_POLICY_REVIEWED,
            CertificationLevel.LEGAL_REVIEWED,
        }:
            raise ValueError("a serving demo policy requires policy review")
        return self


class CorpusManifest(ContractModel):
    schema_version: Literal[1]
    corpus_generation: NonEmptyString
    as_of_date: dt.date
    active_jurisdictions: tuple[NonEmptyString, ...]
    active_topics: tuple[NonEmptyString, ...]
    production_legal_reviewed: bool
    inventory_roots: tuple[NonEmptyString, ...]
    sources: tuple[ManifestSource, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        for values, label in (
            (self.active_jurisdictions, "active_jurisdictions"),
            (self.active_topics, "active_topics"),
            (self.inventory_roots, "inventory_roots"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} values must be unique")

        source_ids = [source.source_id for source in self.sources]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("source_id values must be unique")
        relative_paths = [source.relative_path for source in self.sources]
        if len(set(relative_paths)) != len(relative_paths):
            raise ValueError("relative_path values must be unique")

        for source in self.sources:
            if source.use is CorpusUse.SERVING:
                if source.jurisdiction not in self.active_jurisdictions:
                    raise ValueError("serving source jurisdiction must be in the active scope")
                if not source.topics or not set(source.topics) <= set(self.active_topics):
                    raise ValueError("serving source topics must be non-empty and inside the active scope")

        if self.production_legal_reviewed and any(
            source.use is CorpusUse.SERVING
            and source.normative_tier is NormativeTier.STATUTORY
            and source.certification_level is not CertificationLevel.LEGAL_REVIEWED
            for source in self.sources
        ):
            raise ValueError("production_legal_reviewed requires legal review of every serving statute")
        return self


class VerifiedCorpus(ContractModel):
    manifest: CorpusManifest
    serving_sources: tuple[ManifestSource, ...]
    corpus_sha256: Sha256


class CorpusIntegrityError(RuntimeError):
    """Stable fail-closed error raised before an unsafe corpus can be used."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _resolve_inside_root(repository_root: Path, relative_path: str) -> Path:
    root = repository_root.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise CorpusIntegrityError("SOURCE_PATH_ESCAPE", relative_path)
    return candidate


def _read_manifest(manifest_path: Path) -> CorpusManifest:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return CorpusManifest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise CorpusIntegrityError("MANIFEST_INVALID", str(exc)) from exc


def _verify_inventory(manifest: CorpusManifest, repository_root: Path) -> None:
    recorded_paths = {source.relative_path for source in manifest.sources}
    for inventory_root in manifest.inventory_roots:
        root = _resolve_inside_root(repository_root, inventory_root)
        if not root.is_dir():
            raise CorpusIntegrityError("INVENTORY_ROOT_MISSING", inventory_root)
        for source_path in root.rglob("*.md"):
            relative_path = source_path.relative_to(repository_root.resolve()).as_posix()
            if relative_path not in recorded_paths:
                raise CorpusIntegrityError("UNACCOUNTED_SOURCE", relative_path)


def _verify_source(source: ManifestSource, repository_root: Path) -> None:
    source_path = _resolve_inside_root(repository_root, source.relative_path)
    if not source_path.is_file():
        raise CorpusIntegrityError("SOURCE_MISSING", source.relative_path)
    source_bytes = source_path.read_bytes()
    try:
        source_text = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CorpusIntegrityError("SOURCE_ENCODING_INVALID", source.source_id) from exc
    canonical_bytes = source_text.replace("\r\n", "\n").replace("\r", "\n").encode()
    actual_hash = hashlib.sha256(canonical_bytes).hexdigest()
    if actual_hash != source.content_sha256:
        raise CorpusIntegrityError("SOURCE_HASH_MISMATCH", source.source_id)
    if (
        source.use is CorpusUse.SERVING
        and source.synthetic
        and not all(marker in source_text.upper() for marker in _SYNTHETIC_BANNER_MARKERS)
    ):
        raise CorpusIntegrityError("SYNTHETIC_BANNER_MISSING", source.source_id)


def _corpus_hash(manifest: CorpusManifest) -> str:
    serving_identity = {
        "corpus_generation": manifest.corpus_generation,
        "as_of_date": manifest.as_of_date.isoformat(),
        "sources": [
            {"source_id": source.source_id, "content_sha256": source.content_sha256}
            for source in sorted(manifest.sources, key=lambda item: item.source_id)
            if source.use is CorpusUse.SERVING
        ],
    }
    canonical = json.dumps(serving_identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def load_verified_corpus(manifest_path: Path, *, repository_root: Path) -> VerifiedCorpus:
    """Load a manifest and verify every declared file before exposing sources."""

    manifest = _read_manifest(manifest_path)
    _verify_inventory(manifest, repository_root)
    for source in manifest.sources:
        _verify_source(source, repository_root)
    serving_sources = tuple(source for source in manifest.sources if source.use is CorpusUse.SERVING)
    return VerifiedCorpus(
        manifest=manifest,
        serving_sources=serving_sources,
        corpus_sha256=_corpus_hash(manifest),
    )
