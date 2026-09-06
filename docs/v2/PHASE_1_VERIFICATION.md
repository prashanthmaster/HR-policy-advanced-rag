# Phase 1 Foundation Verification

**Status:** accepted

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

## Remote acceptance evidence

- The owner confirmed removal of the exposed Google authorization and deletion
  of the retired OAuth client on 2026-09-06.
- Commit `50d3998c152494538d83f30a9d4a14e67fded519` was pushed to
  `brownfield-v2`.
- GitHub Actions run `34022994742` completed successfully on its first attempt.
- Every pinned CI step passed, including locked installation, lint, format,
  strict typing, warning-free tests, package build, and the previously open
  Docker image build.

Phase 0 and Phase 1 are accepted. Their exit conditions are closed.

No RAG, legal-correctness, retrieval-quality, guardrail-effectiveness, or
production-readiness claim follows from this foundation checkpoint.
