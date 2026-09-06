"""Fail-closed corpus certification contracts and loading."""

from hr_policy_rag.corpus.manifest import (
    CertificationLevel,
    CorpusIntegrityError,
    CorpusManifest,
    CorpusUse,
    ManifestSource,
    PdfPageRange,
    SourceKind,
    SourceMediaType,
    VerifiedCorpus,
    load_verified_corpus,
)

__all__ = [
    "CertificationLevel",
    "CorpusIntegrityError",
    "CorpusManifest",
    "CorpusUse",
    "ManifestSource",
    "PdfPageRange",
    "SourceKind",
    "SourceMediaType",
    "VerifiedCorpus",
    "load_verified_corpus",
]
