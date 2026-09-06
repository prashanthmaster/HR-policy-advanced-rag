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
from itertools import pairwise
from pathlib import Path, PurePosixPath
from typing import Literal, Self

from pydantic import Field, HttpUrl, model_validator

from hr_policy_rag.domain.models import ContractModel, NonEmptyString, NormativeTier, Sha256

_SYNTHETIC_BANNER_MARKERS = (
    "SYNTHETIC DOCUMENT",
    "NOT A REAL COMPANY POLICY",
)
_INVENTORY_SUFFIXES = {".md", ".pdf", ".docx", ".html", ".htm"}
_OFFICIAL_SOURCE_HOSTS = frozenset(
    {
        "egazette.gov.in",
        "labour.gov.in",
        "mohre.gov.ae",
        "pib.gov.in",
        "uaelegislation.gov.ae",
        "www.egazette.gov.in",
        "www.labour.gov.in",
        "www.mohre.gov.ae",
        "www.pib.gov.in",
        "www.uaelegislation.gov.ae",
    }
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


class SourceMediaType(StrEnum):
    """Physical representation retained in the corpus inventory."""

    MARKDOWN = "text/markdown"
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    HTML = "text/html"


class SourceKind(StrEnum):
    """Document role, distinct from its statutory/company precedence tier."""

    PRIMARY_LAW = "PRIMARY_LAW"
    SUBORDINATE_LAW = "SUBORDINATE_LAW"
    OFFICIAL_GUIDANCE = "OFFICIAL_GUIDANCE"
    REVIEWED_EXTRACT = "REVIEWED_EXTRACT"
    COMPANY_POLICY = "COMPANY_POLICY"
    COMPANY_FAQ = "COMPANY_FAQ"
    COMPANY_PROCEDURE = "COMPANY_PROCEDURE"
    TEST_FIXTURE = "TEST_FIXTURE"
    LEGACY = "LEGACY"


_MEDIA_SUFFIXES: dict[SourceMediaType, frozenset[str]] = {
    SourceMediaType.MARKDOWN: frozenset({".md"}),
    SourceMediaType.PDF: frozenset({".pdf"}),
    SourceMediaType.DOCX: frozenset({".docx"}),
    SourceMediaType.HTML: frozenset({".html", ".htm"}),
}


class PdfPageRange(ContractModel):
    """Inclusive, one-based PDF page range approved for extraction."""

    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.end_page < self.start_page:
            raise ValueError("end_page must be on or after start_page")
        return self


class ManifestSource(ContractModel):
    source_id: NonEmptyString
    title: NonEmptyString | None = None
    document_version: NonEmptyString | None = None
    relative_path: NonEmptyString
    content_sha256: Sha256
    media_type: SourceMediaType = SourceMediaType.MARKDOWN
    source_kind: SourceKind = SourceKind.LEGACY
    use: CorpusUse
    jurisdiction: NonEmptyString
    topics: tuple[NonEmptyString, ...]
    normative_tier: NormativeTier
    synthetic: bool
    certification_level: CertificationLevel
    official_source_urls: tuple[HttpUrl, ...] = ()
    approved_locators: tuple[NonEmptyString, ...] = ()
    approved_page_ranges: tuple[PdfPageRange, ...] = ()
    reason_codes: tuple[NonEmptyString, ...] = ()
    published_on: dt.date | None = None
    effective_from: dt.date | None = None
    effective_to: dt.date | None = None
    reviewed_on: dt.date | None = None
    supersedes: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        relative_path = PurePosixPath(self.relative_path)
        if relative_path.is_absolute() or ".." in relative_path.parts or "\\" in self.relative_path:
            raise ValueError("relative_path must be a repository-relative POSIX path without traversal")
        if len(set(self.topics)) != len(self.topics):
            raise ValueError("topics must not contain duplicates")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")
        if len(set(self.approved_locators)) != len(self.approved_locators):
            raise ValueError("approved_locators must not contain duplicates")
        page_ranges = [(page_range.start_page, page_range.end_page) for page_range in self.approved_page_ranges]
        if page_ranges != sorted(page_ranges):
            raise ValueError("approved_page_ranges must be sorted")
        if any(current[0] <= prior[1] for prior, current in pairwise(page_ranges)):
            raise ValueError("approved_page_ranges must not overlap")
        if self.media_type is not SourceMediaType.PDF and self.approved_page_ranges:
            raise ValueError("approved_page_ranges are valid only for PDF sources")
        if len(set(self.supersedes)) != len(self.supersedes):
            raise ValueError("supersedes must not contain duplicates")
        if self.source_id in self.supersedes:
            raise ValueError("a source cannot supersede itself")
        if self.effective_to is not None and (self.effective_from is None or self.effective_to <= self.effective_from):
            raise ValueError("effective_to requires and must be later than effective_from")

        if self.use is not CorpusUse.SERVING:
            if not self.reason_codes:
                raise ValueError("a non-serving source requires at least one reason code")
            return self

        if self.reason_codes:
            raise ValueError("a serving source cannot carry quarantine or deferral reason codes")
        if self.title is None or self.document_version is None:
            raise ValueError("a serving source requires title and document_version")
        if self.published_on is None or self.effective_from is None or self.reviewed_on is None:
            raise ValueError("a serving source requires published_on, effective_from, and reviewed_on")
        if self.media_type is SourceMediaType.PDF and not self.approved_page_ranges:
            raise ValueError("a serving PDF requires approved_page_ranges")
        if self.normative_tier is NormativeTier.STATUTORY:
            if self.source_kind not in {
                SourceKind.PRIMARY_LAW,
                SourceKind.SUBORDINATE_LAW,
                SourceKind.OFFICIAL_GUIDANCE,
                SourceKind.REVIEWED_EXTRACT,
            }:
                raise ValueError("a serving statutory source requires a statutory source_kind")
            if self.synthetic:
                raise ValueError("a serving statutory source cannot be synthetic")
            if not self.official_source_urls:
                raise ValueError("a serving statutory source requires an official source URL")
            if not self.approved_locators:
                raise ValueError("a serving statutory source requires at least one approved locator")
            if any(url.host not in _OFFICIAL_SOURCE_HOSTS for url in self.official_source_urls):
                raise ValueError("a serving statutory source URL must use an approved official domain")
            if self.certification_level not in {
                CertificationLevel.PRIMARY_SOURCE_CHECKED,
                CertificationLevel.LEGAL_REVIEWED,
            }:
                raise ValueError("a serving statutory source requires primary-source certification")
        else:
            if self.source_kind not in {
                SourceKind.COMPANY_POLICY,
                SourceKind.COMPANY_FAQ,
                SourceKind.COMPANY_PROCEDURE,
            }:
                raise ValueError("a serving company source requires a company source_kind")
            if not self.synthetic:
                raise ValueError("a serving demo company policy must be explicitly synthetic")
            if self.certification_level not in {
                CertificationLevel.DEMO_POLICY_REVIEWED,
                CertificationLevel.LEGAL_REVIEWED,
            }:
                raise ValueError("a serving demo policy requires policy review")
        if self.synthetic and self.media_type not in {SourceMediaType.MARKDOWN, SourceMediaType.HTML}:
            raise ValueError("a serving synthetic binary requires a Phase 3 content-aware banner validator")
        return self


class CorpusManifest(ContractModel):
    schema_version: Literal[1, 2, 3]
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

        by_id = {source.source_id: source for source in self.sources}
        for source in self.sources:
            for prior_id in source.supersedes:
                prior = by_id.get(prior_id)
                if prior is None:
                    raise ValueError(f"source {source.source_id} supersedes unknown source {prior_id}")
                if prior.jurisdiction != source.jurisdiction or prior.normative_tier is not source.normative_tier:
                    raise ValueError("a source may supersede only the same jurisdiction and normative tier")
                if (
                    source.effective_from is not None
                    and prior.effective_from is not None
                    and source.effective_from <= prior.effective_from
                ):
                    raise ValueError("a successor must become effective after its predecessor")
                if prior.effective_to is not None and prior.effective_to != source.effective_from:
                    raise ValueError("a predecessor effective_to must equal its successor effective_from")

        def visit(source_id: str, trail: frozenset[str]) -> None:
            if source_id in trail:
                raise ValueError("source supersession graph must be acyclic")
            for prior_id in by_id[source_id].supersedes:
                visit(prior_id, trail | {source_id})

        for source_id in by_id:
            visit(source_id, frozenset())

        for source in self.sources:
            if source.use is CorpusUse.SERVING:
                if source.jurisdiction not in self.active_jurisdictions:
                    raise ValueError("serving source jurisdiction must be in the active scope")
                if not source.topics or not set(source.topics) <= set(self.active_topics):
                    raise ValueError("serving source topics must be non-empty and inside the active scope")
                if source.reviewed_on is not None and source.reviewed_on > self.as_of_date:
                    raise ValueError("serving source reviewed_on cannot be later than the manifest as_of_date")

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
        for source_path in root.rglob("*"):
            if not source_path.is_file() or source_path.suffix.lower() not in _INVENTORY_SUFFIXES:
                continue
            relative_path = source_path.relative_to(repository_root.resolve()).as_posix()
            if relative_path not in recorded_paths:
                raise CorpusIntegrityError("UNACCOUNTED_SOURCE", relative_path)


def _verify_source(source: ManifestSource, repository_root: Path) -> None:
    source_path = _resolve_inside_root(repository_root, source.relative_path)
    if not source_path.is_file():
        raise CorpusIntegrityError("SOURCE_MISSING", source.relative_path)
    if source_path.suffix.lower() not in _MEDIA_SUFFIXES[source.media_type]:
        raise CorpusIntegrityError("SOURCE_MEDIA_TYPE_MISMATCH", source.source_id)
    source_bytes = source_path.read_bytes()
    source_text: str | None = None
    if source.media_type in {SourceMediaType.MARKDOWN, SourceMediaType.HTML}:
        try:
            source_text = source_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise CorpusIntegrityError("SOURCE_ENCODING_INVALID", source.source_id) from exc
        canonical_bytes = source_text.replace("\r\n", "\n").replace("\r", "\n").encode()
    else:
        canonical_bytes = source_bytes
    actual_hash = hashlib.sha256(canonical_bytes).hexdigest()
    if actual_hash != source.content_sha256:
        raise CorpusIntegrityError("SOURCE_HASH_MISMATCH", source.source_id)
    if (
        source.use is CorpusUse.SERVING
        and source.synthetic
        and source_text is not None
        and not all(marker in source_text.upper() for marker in _SYNTHETIC_BANNER_MARKERS)
    ):
        raise CorpusIntegrityError("SYNTHETIC_BANNER_MISSING", source.source_id)


def _corpus_hash(manifest: CorpusManifest) -> str:
    serving_identity = {
        "schema_version": manifest.schema_version,
        "corpus_generation": manifest.corpus_generation,
        "as_of_date": manifest.as_of_date.isoformat(),
        "active_jurisdictions": manifest.active_jurisdictions,
        "active_topics": manifest.active_topics,
        "production_legal_reviewed": manifest.production_legal_reviewed,
        "sources": [
            source.model_dump(mode="json")
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
