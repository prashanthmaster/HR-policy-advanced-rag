# HR-Policy RAG — quality-first brownfield rebuild

This repository is rebuilding a version-aware HR-policy question-answering
system. The original implementation is preserved at tag `v1-audit-baseline`.
Only code under `src/hr_policy_rag` and the `corpus_v2` manifest are active v2
work.

The portfolio objective is an evidence-linked system for India and UAE
mainland gratuity/end-of-service, notice, and leave questions. It must select
the rule applicable on a requested date, distinguish mandatory law from
synthetic company policy, calculate deterministically, and refuse or clarify
when evidence or employee facts are insufficient.

## Verified status

| Gate | Status | Evidence |
|---|---|---|
| Phase 0 — security and v1 preservation | Accepted | `v1-audit-baseline` |
| Phase 1 — reproducible foundation | Accepted | commit `50d3998`, Actions run `34022994742` |
| Phase 2A — certified India-gratuity seed | Accepted | commit `0f5c554`, Actions run `34025628818` |
| Phase 2B — professional portfolio corpus | Accepted | commit `5c8a02a`, Actions run `34028191410` |
| Phase 3 — deterministic ingestion | Accepted | commit `94c8b7d`, Actions run `34031374720` |
| Phase 4A — hybrid retrieval contracts | Local candidate | real-Qdrant CI pending |
| Phase 4B — measured retrieval quality | Blocked | real embedding evaluation not yet run |
| Phases 5–10 | Not started | no answer-quality or production claim |

## Phase 2B corpus profile

The checked-in v2 manifest currently exposes:

- 33 serving source records across `GLOBAL`, `India`, and `UAE`;
- gratuity/end-of-service, notice, and leave coverage in both active countries;
- 4 locally verified official India PDFs containing 188 pages and approximately
  87,811 words before deterministic Phase 3 extraction;
- reviewed UAE statutory extracts whose official raw endpoints are recorded as
  remote-only because automated acquisition was blocked;
- 22 conspicuously synthetic company-policy, procedure, and FAQ records;
- 8 explicit historical-to-current supersession relationships;
- 10 adversarial fixtures that cannot enter the serving set;
- all 8 legacy v1 documents explicitly quarantined or deferred.

These figures describe corpus inventory, not retrieval performance. The PDF word
counts are profiling observations and are not accepted ingestion output.

`production_legal_reviewed` remains `false`. Primary-source checking makes this
suitable for a bounded portfolio demonstration; it does not make the project
legal advice or production HR software.

## Corpus controls

`corpus_v2/manifest.json` is generated deterministically from
`scripts/build_corpus_manifest.py`. A file cannot become serving material merely
by being copied into a directory.

The verifier rejects:

- missing, changed, or unaccounted source files;
- path traversal and media-type/extension mismatches;
- statutory sources outside the approved official-domain allowlist;
- unreviewed serving sources or unlabeled synthetic company policies;
- invalid effective-date ranges, unknown predecessors, and cyclic lineage;
- adversarial, quarantined, or deferred material leaking into the serving set.

Raw PDF hashes use exact bytes. UTF-8 Markdown and HTML hashes normalize only an
optional BOM and line endings so Windows and Linux produce the same identity.

## Phase 3 ingestion profile

The checked-in deterministic ingestion artifact currently contains 126 chunks
from all 33 serving records. It extracts 92,145 characters: 58,400 from 25
approved PDF pages and 33,745 from reviewed Markdown. Archived-but-unapproved
PDF pages, adversarial fixtures, quarantined files, and deferred files produce
no chunks.

Chunks are bounded at 1,600 characters with 160 characters of lexical overlap.
They preserve source and content hashes, document version, jurisdiction, topic,
authority tier, publication/effective dates, supersession, page or heading
locator, and parser/chunker versions. Clause-structured Markdown retains clause
IDs as locators without embedding its control metadata as policy prose.

Markdown and PDF are the only supported serving formats because they are the
only formats backed by reviewed corpus samples. Encrypted, malformed, textless,
oversized, and out-of-range PDFs fail closed. HTML and DOCX remain unsupported
instead of being claimed from mocks; scanned PDFs require a future reviewed OCR
path.

## Target architecture

The serving path will remain deliberately small:

1. FastAPI validates the request and required employee facts.
2. A verified corpus generation produces deterministic chunks and lineage.
3. Qdrant performs metadata-filtered dense+sparse retrieval and fusion.
4. Deterministic policy logic selects the governing version and performs
   calculations.
5. A language model explains the supported decision in a strict schema.
6. Output validation checks claims, evidence, calculations, citations, safety,
   and supersession before release.

No LangChain, LangGraph, separate BM25 store, Redis, or guardrail agent is part
of the initial serving path.

## Run the current quality gate

Python 3.12 and `uv` 0.11 are required.

```bash
uv sync --locked --all-groups
uv lock --check
uv run ruff check src tests_v2 scripts/build_corpus_manifest.py scripts/build_ingestion_artifact.py
uv run ruff format --check src tests_v2 scripts/build_corpus_manifest.py scripts/build_ingestion_artifact.py
uv run pyright
uv run pytest --cov=hr_policy_rag --cov-report=term-missing tests_v2
uv run python scripts/build_corpus_manifest.py --check
uv run python scripts/build_ingestion_artifact.py --check
uv build
docker build --tag hr-policy-rag:local .
```

## Evidence and decisions

- `docs/v2/QUALITY_CONTRACT.md`
- `docs/v2/ADR-0001-BROWNFIELD-BOUNDARY.md`
- `docs/v2/ADR-0002-CORPUS-CERTIFICATION.md`
- `docs/v2/ADR-0003-PROFESSIONAL-CORPUS-PROFILE.md`
- `docs/v2/ADR-0004-DETERMINISTIC-INGESTION.md`
- `docs/v2/PHASE_2B_VERIFICATION.md`
- `docs/v2/PHASE_3_VERIFICATION.md`
- `corpus_v2/acquisition_status.json`

No performance number or “production-grade” description should be used in a
resume or interview unless the corresponding immutable evaluation evidence is
present in this repository.
