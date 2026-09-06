# Phase 3 Deterministic Ingestion Verification

**Status:** local candidate; remote CI pending

**Branch:** `brownfield-v2`

**Corpus generation:** `india-uae-policy-portfolio-2026-09-06-v1`

**Corpus SHA-256:** `43f5fbfa14e696713334dab1420b1a3bd5984dfbf241d5f4feda3a4d1f5edb2c`

**Ingestion generation:** `d3d8682600bb4c80abd5eff2ea8decc0b9e066ab97c4f3df716258aa13dc4d59`

**Chunks SHA-256:** `815e7d6bf282eb5d19921a3e0504f43f27029117a950cb10e63e737519a81bd1`

## Observed artifact

| Measure | Candidate evidence |
|---|---:|
| Serving sources represented | 33 of 33 |
| Excluded sources represented | 0 |
| Generated chunks | 126 |
| Extracted characters | 92,145 |
| Approved PDF pages extracted | 25 |
| Archived PDF pages | 188 |
| Approved PDF characters | 58,400 |
| Markdown characters | 33,745 |
| Minimum chunk length | 160 characters |
| Median chunk length | 778.5 characters |
| Maximum chunk length | 1,600 characters |
| Duplicate chunk IDs | 0 |
| Duplicate chunk text hashes | 0 |

Four handbook chapter-title pages initially produced 112–154 character chunks
with no substantive rule text. The quality audit removed those pages from the
approved ranges before this candidate was recorded. The underlying PDFs remain
unchanged and fully archived.

## Provenance contract

Every chunk records:

- stable chunk ID and content hash;
- source ID and exact source-content hash;
- document title and version;
- jurisdiction and topics;
- statutory/company authority tier and source kind;
- synthetic status;
- publication and effective dates;
- superseded source IDs;
- approved legal locators;
- Markdown heading/clause locator or exact PDF page;
- chunk ordinal and schema version.

The companion manifest records corpus identity, parser versions, chunker
configuration, per-source counts, extracted pages, parser warnings, chunk-file
hash, and ingestion-generation hash.

The corpus hash covers the complete serving metadata record as well as source
content. A change to an effective date, approved page range, legal locator,
jurisdiction, topic, authority tier, or supersession relationship therefore
changes corpus identity even when file bytes remain unchanged. A regression
test first demonstrated that the Phase 2 hash did not provide this guarantee.

## Acceptance and failure tests

- Two independent in-process builds render byte-identical JSONL and manifests.
- Checked-in artifacts must exactly match a fresh build.
- Every serving source and only a serving source produces chunks.
- Every PDF source exposes exactly its manifest-approved pages.
- Critical Code on Social Security, Code on Wages, Ministry FAQ, and employer
  handbook passages survive extraction.
- Synthetic warning text remains visible while clause control metadata is not
  treated as embedding prose.
- Adversarial prompt injection, fabricated law, false threshold, and wrong wage
  basis text never appears in a serving chunk.
- Malformed, encrypted, textless, oversized, and out-of-range PDFs fail closed.
- Malformed clause blocks and unsupported media types fail closed.
- Chunk text rejects NUL, Unicode replacement characters, empty text, and text
  beyond the configured maximum.

## Recorded parser condition

`in-wages-2019-raw` causes `pypdf` to report that its cross-reference table is
not zero-indexed and object IDs will be corrected. The warning is stored in the
source summary. The document's page count, approved range, and critical
`one-half` wage-definition passage pass real extraction checks. No other serving
source produced a parser warning.

## Explicit non-claims

Phase 3 does not prove:

- OCR for scanned PDFs;
- DOCX or HTML ingestion;
- semantic optimality of the 1,600/160 chunking choice;
- embedding or Qdrant indexing behaviour;
- retrieval recall or precision;
- temporal policy selection, calculation, or final-answer quality.

Chunk-size effectiveness becomes an evaluated variable in Phase 4. It will not
be tuned from intuition alone.

## Local verification evidence

| Check | Observed result |
|---|---|
| `uv lock --check` | Passed; 36 packages resolved |
| Ruff lint and format | Passed for 24 active v2 code, test, and builder files |
| Pyright strict mode | 0 errors, 0 warnings |
| Full v2 test suite | 59 passed; warnings are errors |
| Coverage | 94.38% against a 90% gate |
| Corpus manifest regeneration | Passed; byte-for-byte reproducible |
| Ingestion artifact regeneration | Passed; byte-for-byte reproducible |
| Package build | Source distribution and wheel built successfully |
| Repository whitespace check | Passed |
| Credential-pattern scan | No match in the candidate text files |
| Local Docker build | Blocked: Docker executable unavailable in this environment |

Phase 3 remains a local candidate until the repository is committed and pushed
and independent GitHub Actions—including the Docker build—passes.
