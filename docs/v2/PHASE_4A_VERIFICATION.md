# Phase 4A verification: contracts and Qdrant integration

- Status: **CANDIDATE — local code gate passed; remote/server and live-quality gates open**
- Date: 2026-09-06
- Base commit: `94c8b7d`

## Implemented

- Frozen, balanced 36-case retrieval exam with independent content digest.
- Provider-neutral dense and sparse encoder contracts.
- Direct OpenAI embedding adapter with order, dimension, and token validation.
- Qdrant-supported BM25 sparse adapter loaded lazily off the event loop.
- Immutable candidate-index builder for all 126 Phase 3 chunks.
- Dense+sparse Qdrant prefetch and RRF in one collection.
- Generation, jurisdiction, topic, and effective-date filters.
- Typed invalid-context, unavailable-dependency, and payload-integrity failures.
- Source-level Recall@10, MRR@10, temporal, leakage, error, and slice metrics.
- Development/release runner that refuses key files and output overwrites.
- Pinned Qdrant `v1.19.1` CI server test for payload indexes and networked RRF.

## Local evidence

`uv run pytest --cov=hr_policy_rag --cov-report=term-missing tests_v2`:

- 89 passed;
- 1 skipped: the explicitly CI-owned network Qdrant test;
- coverage: 92.28%, above the 90% gate.

Other gates:

- Ruff lint and format: passed;
- Pyright strict: 0 errors, 0 warnings;
- `uv lock --check`: passed;
- missing `OPENAI_API_KEY`: explicit failure and no output artifact.

The project and CI use `uv 0.12.9` exactly. This was corrected after the first
Windows evaluation attempt demonstrated that the earlier `<0.12` constraint
rejected the developer's installed stable toolchain.

## Open gates

Phase 4A is accepted only after GitHub Actions passes against pinned Qdrant.

Phase 4B remains open until:

1. a real development/regression run uses OpenAI `text-embedding-3-small` and
   `Qdrant/bm25`;
2. any changes use development evidence only;
3. thresholds and holdout content remain unchanged;
4. one release run includes all 36 cases;
5. every frozen aggregate and slice gate passes;
6. the immutable result records commit, lockfile, corpus, case-set, index,
   models, tokens, row results, errors, and exclusions.

No retrieval-quality claim is made from deterministic test encoders.
