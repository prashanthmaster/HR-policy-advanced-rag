# ADR-0002: Certify one narrow corpus before ingestion

- **Status:** accepted
- **Date:** 2026-09-06
- **Decision owner:** Prashanth

## Context

The legacy corpus cannot be treated as a trusted input merely because it is
labelled Tier 1 or Tier 2. Primary-source review found material defects:

- India's four Labour Codes became effective on 21 November 2025, while the
  legacy file still describes pre-Code statutes as the current baseline.
- The legacy India extract invents a general four-year gratuity threshold from
  1 April 2026. The Ministry's March 2026 FAQ retains five years for ordinary
  employees and records the one-year rule specifically for fixed-term
  employees.
- Some statutory clauses cite a ministry homepage or private legal commentary
  instead of the governing official instrument.
- The legacy DIFC extract says carry-forward is limited to five working days.
  The July 2025 consolidated official law permits accrued leave to carry for up
  to twelve months and prevents an employer from restricting rollover below
  five working days; those are not the same rule.
- Synthetic policy and deliberate adversarial defects share source files, so a
  file-level allowlist cannot separate them safely.

## Decision

Phase 2 starts with one active vertical slice: **India gratuity**. The serving
corpus consists only of:

1. a project-prepared statutory extract checked against the Code on Social
   Security, its commencement notification, and the Ministry's March 2026 FAQ;
2. a conspicuously synthetic Meridian India gratuity policy that cannot reduce
   the statutory floor.

The manifest at `corpus_v2/manifest.json` is the only allowlist. Every source
has an immutable canonical content hash and one explicit use:

- `SERVING`
- `ADVERSARIAL_TEST`
- `QUARANTINED`
- `DEFERRED`

Every Markdown document under the declared inventory roots must appear in the
manifest. An unrecorded file, missing file, changed hash, path escape, missing
official statutory provenance, or missing synthetic-policy banner stops corpus
loading.

Hashes are computed after decoding UTF-8, removing an optional BOM, and
normalizing line endings to LF. This makes the corpus identity reproducible on
Windows and Linux without weakening content-integrity checks.

`PRIMARY_SOURCE_CHECKED` means suitable for this bounded portfolio demo. It
does **not** mean lawyer-reviewed or production legal advice. The manifest
records `production_legal_reviewed: false`, and the certified extract excludes
the monetary ceiling until a current post-Code notification is captured and
reviewed.

## Consequences

- Retrieval cannot accidentally ingest any legacy or adversarial document.
- The initial system can prove one end-to-end behavior before expanding to UAE,
  notice, leave, DIFC, or Germany.
- Legal scope gaps become explicit refusals or later review work, not guessed
  answers.
- Expansion requires a new manifest generation, source review, tests, and
  corpus hash; copying a file into a folder is insufficient.
