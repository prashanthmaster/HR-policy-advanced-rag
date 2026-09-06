# Phase 1 Foundation Verification

**Status:** local candidate; not yet accepted

**Branch:** `brownfield-v2`

**Preserved baseline:** `v1-audit-baseline` at
`d4138eb0cafcec6e8fd9e43417d40df7d08e3910`

## Implemented boundary

- Python 3.12 is the only supported interpreter line.
- `pyproject.toml` and committed `uv.lock` are the only active dependency
  definition and resolution files.
- The v2 package is isolated under `src/hr_policy_rag`; legacy modules are not
  imported by the package or copied into the image.
- Runtime configuration is immutable, validated, and read through one settings
  class.
- Canonical domain models reject extra fields and enforce initial provenance,
  temporal, case-fact, evidence, claim, answer, and run-manifest invariants.
- Provider-neutral protocols define the corpus, retrieval, generation,
  guardrail, publication, and telemetry seams.
- FastAPI is the only serving process. `/live`, `/ready`, `/version`, and `/`
  have typed behavior.
- Request correlation accepts a conservative caller ID or replaces it with a
  generated UUID. Application logs use a JSON envelope and do not log query
  bodies.

## Local evidence recorded on 2026-09-06

| Check | Observed result |
|---|---|
| `uv lock --check` | Passed; 35 packages resolved |
| `uv run ruff check src tests_v2` | Passed |
| `uv run ruff format --check src tests_v2` | Passed |
| `uv run pyright` | Passed after correcting test annotations |
| `uv run pytest --cov=hr_policy_rag tests_v2` | 19 passed; warnings are errors; 96.79% coverage against a 90% gate |
| `uv build` | Source distribution and wheel built successfully |
| Uvicorn smoke | All four endpoints returned HTTP 200; startup and shutdown completed cleanly |
| `git diff --check` | Passed |
| Changed-file credential-pattern scan | No match; this is a narrow hygiene check, not a complete security audit |

## Open exit conditions

1. The container image has not been built locally because this executor has no
   Docker, Podman, or Buildah binary. The pinned CI workflow must execute the
   Docker build before Phase 1 is accepted.
2. The previously uploaded Google OAuth grants must be revoked by the owner.
   No uploaded token was used during this work. Until revocation is confirmed,
   Phase 0 remains open.
3. CI has not run on the local branch because no remote push was authorized.

No RAG, legal-correctness, retrieval-quality, guardrail-effectiveness, or
production-readiness claim follows from this foundation checkpoint.
