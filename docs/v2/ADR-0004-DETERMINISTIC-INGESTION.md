# ADR-0004: Use page-gated deterministic ingestion

- **Status:** accepted
- **Date:** 2026-09-06
- **Decision owner:** Prashanth

## Context

Phase 2B retained 188 official PDF pages but approved only specific statutory
sections for the portfolio scope. Indexing every archived page would confuse
document possession with evidence approval. It would also increase irrelevant
retrieval candidates and allow unreviewed provisions to influence answers.

The serving corpus currently contains Markdown and PDF. It contains no approved
DOCX or HTML source and no scanned source requiring OCR. Supporting those formats
only through synthetic unit fixtures would create the same gap between claims and
real behaviour found in v1.

## Decision

Ingestion is a deterministic build step, not a request-time operation.

- The corpus manifest is upgraded to schema version 3 and records inclusive,
  one-based `approved_page_ranges` for every serving PDF.
- Only serving records enter ingestion. PDF pages outside their approved ranges
  never reach the chunker.
- Markdown is segmented by ATX headings. The existing clause-structured format
  is segmented by its real clause IDs while control metadata is excluded from
  embedding text.
- PDF text is extracted with locked `pypdf` 6.17 in strict, layout-aware mode.
  Encrypted, malformed, textless, oversized, and out-of-range content fails with
  stable error codes.
- Chunks use a versioned 1,600-character word boundary with 160 characters of
  overlap. Their identifiers are hashes of source identity, locator, content,
  ordinal, and chunker version.
- JSONL chunks and a companion manifest are committed under
  `artifacts/v2/ingestion` and reproduced byte-for-byte in CI.
- Parser warnings are retained per source. They are evidence, not console noise
  to be silently suppressed.
- DOCX, HTML, and OCR are explicitly unsupported until reviewed real samples and
  corresponding acceptance tests exist.

`pypdf` is used directly instead of introducing a document framework. It is
pure Python and keeps the container and dependency boundary small. Its official
documentation also warns that PDF text extraction has structural limitations and
may consume substantial memory for unusually large streams; the adapter therefore
caps each approved page's decoded content stream at 20 MB.

## Consequences

- The current artifact contains 126 chunks from all 33 serving records.
- Only 25 of the 188 archived PDF pages are admitted, yielding 58,400 approved
  PDF characters rather than an unreviewed full-document dump.
- Exact regeneration is possible because corpus hash, parser versions, chunker
  settings, chunk hashes, and the ingestion-generation hash are recorded.
- Corpus identity now covers the complete serving metadata record, so changing
  an approved page, effective date, locator, scope, or lineage changes the hash
  even if the underlying file bytes do not.
- A Code on Wages PDF cross-reference warning is preserved in the artifact. Its
  approved pages and critical passages still pass integration assertions.
- Phase 3 establishes input determinism and provenance. It does not establish
  embedding, indexing, retrieval, temporal-decision, or answer quality.

## References

- pypdf text extraction:
  https://pypdf.readthedocs.io/en/latest/user/extract-text.html
- pypdf strictness and robustness:
  https://pypdf.readthedocs.io/en/latest/user/robustness.html
