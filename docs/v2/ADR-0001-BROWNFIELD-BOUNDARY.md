# ADR-0001: Preserve v1 and build an isolated v2

- **Status:** accepted
- **Date:** 2026-09-06
- **Decision owner:** Prashanth

## Context

The first implementation contains useful domain work and extensive mechanical
tests, but its corpus truth, retrieval generations, runtime guardrails,
freshness path, and evaluation artifacts are not aligned. Continuing to patch
those seams would make behavioural ownership harder to establish.

## Decision

The GitHub state at commit `d4138eb0cafcec6e8fd9e43417d40df7d08e3910`
is preserved by the local tag `v1-audit-baseline`. New work occurs on
`brownfield-v2` under `src/hr_policy_rag` and `tests_v2`.

V1 code and tests remain temporarily available as migration evidence. They are
not part of the v2 package or v2 test gate. Each migrated capability must meet
the v2 quality contract before the corresponding legacy path is removed.

The separately supplied Session-11 fact-extraction files are preserved as
historical inputs but are not merged directly. Their behaviour will be
reimplemented only after the v2 case-fact contract is approved.
## Consequences

- A clean v2 can be verified without claiming that legacy tests prove it.
- Migration requires explicit decisions instead of implicit imports.
- Temporary duplication exists, but its removal is a milestone requirement.
