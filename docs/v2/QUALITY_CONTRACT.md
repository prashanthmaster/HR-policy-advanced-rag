# V2 Quality Contract

This document is normative for the brownfield rebuild.

## Stop-the-line rule

A phase is complete only when its recorded exit criteria pass. A failed or
blocked phase cannot be marked complete and cannot be compensated for in a
higher layer.

## Required engineering behaviour

1. Write an acceptance or regression test before correcting a defect.
2. Fix the lowest layer that owns the violated invariant.
3. Do not put probe IDs, golden-query text, or one-off clause IDs in generic runtime logic.
4. Do not convert dependency failure into an ordinary empty result.
5. Every fallback must be typed, logged, observable, and tested.
6. Use one canonical schema, one settings source, one active runtime path, and one index generation per answer.
7. Freeze thresholds before holdout evaluation.
8. Never combine metrics from different run manifests.
9. Remove or archive the replaced path within the same milestone.
10. Do not describe generated code as complete until real behaviour is verified.

## Definition of done

A change is done only when:

- acceptance, negative, and failure tests pass;
- linting and strict type checking pass;
- required integrations have a real smoke test;
- errors have stable codes and sufficient telemetry;
- documentation describes the observed behaviour;
- no unexplained fallback or critical-path TODO remains;
- the relevant quality gate passes.
