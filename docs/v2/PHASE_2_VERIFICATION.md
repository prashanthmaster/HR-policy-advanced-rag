# Phase 2 Corpus Truth Verification

**Status:** local candidate; remote CI pending

**Branch:** `brownfield-v2`

**Active slice:** India gratuity

## Certified generation

- Generation: `india-gratuity-demo-2026-09-06-v1`
- Canonical corpus SHA-256:
  `486758ac242ac94c80923fa3fa5506e61100f09c62690d4087dc200ff45632eb`
- Serving sources: 2
- Production legal review: false

The two serving sources are the primary-source-checked statutory demo extract
and the conspicuously synthetic Meridian gratuity policy. The monetary ceiling
is excluded from the certified scope because the project has not captured and
reviewed a current post-Code ceiling notification.

## Source-truth corrections

| Legacy claim or structure | Phase 2 disposition |
|---|---|
| Pre-2020 statutes are the current India baseline | Quarantined; the four Labour Codes became effective 2025-11-21 |
| Ordinary gratuity threshold became four years on 2026-04-01 | Rejected as false; five years remains the ordinary rule |
| One-year eligibility | Scoped only to directly engaged fixed-term employees |
| India statute citations to private commentary/homepages | Not permitted for a serving statutory source |
| DIFC carry-forward is capped at five days | Marked incorrect and deferred from the active slice |
| Deliberate defects mixed into serving-like policy files | Legacy files quarantined; false claim moved to adversarial-only fixture |

## Machine-enforced invariants

- The manifest is strict, immutable, and versioned.
- Serving statutes require official provenance and primary-source or legal
  certification.
- Serving demo policies must be synthetic, reviewed, and visibly bannered.
- Non-serving sources require stable reason codes.
- Every source ID and path is unique.
- Serving jurisdictions and topics must remain inside the active scope.
- Every Markdown file under the inventory roots is accounted for.
- Missing files, changed canonical hashes, invalid encodings, and repository
  path escapes fail closed with stable error codes.
- Adversarial, quarantined, and deferred sources are absent from the returned
  serving set.
- Corpus identity is deterministic across BOM and Windows/Linux line endings.

## Primary sources checked

- Code on Social Security, 2020, Chapter V, sections 53–54:
  https://www.labour.gov.in/static/uploads/2025/07/b0620548445580767b5c0d18c95c26f7.pdf
- Gazette commencement notification S.O. 5319(E), 21 November 2025:
  https://egazette.gov.in/WriteReadData/2025/267882.pdf
- Ministry of Labour and Employment, Additional FAQs on Labour Codes,
  16 March 2026:
  https://www.labour.gov.in/static/uploads/2026/03/a4ccf4c6d97c4f1f36a6d83f8c64213d.pdf
- DIFC Employment Law consolidated official PDF dated July 2025:
  https://edge.sitecorecloud.io/dubaiintern0078-difcexperie96c5-production-3253/media/project/difcexperiences/difc/difcwebsite/documents/laws--regulations/employment-law.pdf

## Exit conditions

1. All local engineering gates must pass.
2. The manifest must verify from a clean checkout in GitHub Actions.
3. The Docker build must remain green.

Passing Phase 2 certifies only the bounded portfolio corpus. It does not claim
that the project is production legal software or that the deferred countries
and topics are correct.

## Local evidence recorded on 2026-09-06

| Check | Observed result |
|---|---|
| `uv lock --check` | Passed; 35 packages resolved |
| Corpus manifest load | Passed; 2 serving sources |
| Canonical corpus hash | `486758ac242ac94c80923fa3fa5506e61100f09c62690d4087dc200ff45632eb` |
| Corpus acceptance/negative tests | 19 passed |
| Full v2 test suite | 38 passed; warnings are errors |
| Coverage | 97.93% against a 90% gate |
| Ruff lint and format | Passed |
| Pyright strict mode | 0 errors, 0 warnings |
| Package build | Source distribution and wheel built successfully |
| `git diff --check` | Passed |
| Changed-file credential-pattern scan | No matches |

The local evidence is complete. Phase 2 remains a candidate until the commit
is pushed and the independent GitHub Actions/Docker gate passes.
