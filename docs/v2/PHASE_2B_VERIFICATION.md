# Phase 2B Professional Corpus Verification

**Status:** local candidate; remote CI pending

**Branch:** `brownfield-v2`

**Corpus generation:** `india-uae-policy-portfolio-2026-09-06-v1`

## Scope and composition

| Measure | Candidate evidence |
|---|---:|
| Serving source records | 33 |
| Statutory/official serving records | 11 |
| Synthetic company serving records | 22 |
| India serving records | 16 |
| UAE serving records | 13 |
| Global procedural/policy records | 4 |
| Locally verified official PDFs | 4 |
| Locally verified official PDF pages | 188 |
| PDF words observed for profile only | 87,811 |
| Historical-to-current lineage edges | 8 |
| Adversarial fixtures | 10 |
| Legacy documents serving | 0 |

The PDF word counts are profiling observations produced outside the application.
They are not accepted Phase 3 extraction output and do not establish chunking or
retrieval behaviour.

## Source acquisition

Locally retained official India artifacts:

- Code on Social Security, 2020 — 116 pages;
- Code on Wages, 2019 — 29 pages;
- Additional FAQs on Labour Codes, 16 March 2026 — five pages;
- Compliance Handbook for Employers Under the Four Labour Codes — 38 pages.

Each is a valid PDF with an exact byte hash recorded in both the manifest and
`corpus_v2/acquisition_status.json`.

The official UAE legislation and MOHRE endpoints blocked or timed out during
automated binary acquisition. No third-party binary was substituted. Reviewed
scope-limited extracts retain the official URLs, and the raw acquisition gap is
recorded as `REMOTE_ONLY`.

## Review matrix

| Jurisdiction/topic | Approved evidence boundary | Deliberate limitation |
|---|---|---|
| India gratuity | Social Security Code sections 2(88), 53–56; Ministry FAQ questions 6–7, 13–14, 16–17, 19 | Monetary ceiling excluded until the current notification is captured and reviewed |
| India notice | Industrial Relations Code/handbook scope plus synthetic contract policy | No invented universal resignation-notice number |
| India leave | OSH Code/official backgrounder scope plus synthetic company entitlement | Establishment and worker coverage must be known |
| UAE end-of-service | Decree-Law Article 51 reviewed extract | Mainland foreign full-time demo case only; no DIFC/ADGM or pension case |
| UAE notice | Decree-Law Articles 9 and 43 reviewed extract | Probation facts and destination must be distinguished |
| UAE leave | Decree-Law Article 29 reviewed extract | Calendar days must not be converted to working days |

All statutory records carry approved locators. Phase 3 may extract only those
sections from a raw source unless a new review expands the manifest.

## Machine-enforced gates

- Every inventory Markdown, PDF, DOCX, and HTML file is declared.
- Raw PDFs use byte-exact hashes; text uses BOM/line-ending canonical hashes.
- Serving statutory URLs use an explicit official-domain allowlist.
- Serving sources require titles, versions, publication/effective/review dates,
  source-kind/tier agreement, and applicable topic/jurisdiction metadata.
- Company source text requires explicit synthetic and non-real-policy markers.
- Supersession references must exist, stay within jurisdiction/tier, follow date
  order, align predecessor end dates, and remain acyclic.
- Ten adversarial documents and all legacy files remain non-serving.
- The portfolio profile covers each India/UAE topic pair with multiple sources.
- The generated manifest must reproduce byte-for-byte in CI.

## Explicit non-claims

Phase 2B does not prove:

- PDF extraction or chunk correctness;
- DOCX/HTML parser behaviour;
- Qdrant indexing or retrieval quality;
- effective-date decision correctness;
- formula accuracy or generated-answer quality;
- production legal approval.

Those claims remain gated in later phases.

## Local verification evidence

| Check | Observed result |
|---|---|
| `uv lock --check` | Passed; 35 packages resolved |
| Manifest regeneration `--check` | Passed; byte-for-byte reproducible |
| Corpus load | Passed; 33 serving sources |
| Corpus SHA-256 | `36ffcaace8e60cba5a765d624ca57bf20f6334bdd559b3dd4d7969dacb8ab75b` |
| Corpus manifest tests | 24 passed |
| Full v2 test suite | 43 passed; warnings are errors |
| Coverage | 95.76% against a 90% gate |
| Ruff lint and format | Passed for active v2 code, tests, and manifest builder |
| Pyright strict mode | 0 errors, 0 warnings |
| Package build | Source distribution and wheel built successfully |
| Local Docker build | Blocked: Docker executable unavailable in this environment |

Phase 2B remains a local candidate until repository hygiene checks pass, the
candidate is committed and pushed, and independent GitHub Actions—including the
Docker image build—passes.
