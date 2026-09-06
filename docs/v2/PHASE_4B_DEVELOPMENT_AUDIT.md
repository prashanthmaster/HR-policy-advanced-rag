# Phase 4B development retrieval audit

- Status: **PASSED — holdout authorized after corrective checkpoint**
- Evaluated commit: `59cb2ef0439c9d9f1762f5cd5144cc589b105249`
- Canonical LF evaluation artifact SHA-256:
  `54f5790f11724f8f5e8723c7aa70330dbb73a36f96cfe04504760eefb8e5514f`
- Submitted Windows CRLF transport SHA-256:
  `25d89e2b3ec83af997c9fe25a76ef4450607ecb1ad2074605f289557ad01c8dd`
- Frozen case-set SHA-256:
  `06d931aec5fcba2b3c6b1f2b33a193397796de4574ae252bfb8198221a76b555`

## Independently recomputed results

- Cases: 24 (12 development + 12 regression)
- Source-group Recall@10: 1.0000
- Mean reciprocal rank@10: 0.9434523809523809
- Temporal-version accuracy: 1.0000
- Filter leakage: 0
- Errors: 0
- Exclusions: 0
- Embedding tokens: 22,257
- Indexed chunks: 126
- Dense model: `text-embedding-3-small`, 1,536 dimensions
- Sparse model: `Qdrant/bm25`

Every jurisdiction/topic slice achieved Recall@10 of 1.00. Slice MRR ranged
from 0.785714 for India gratuity to 1.00.

Two targets were not rank 1:

- India post-commencement statutory wage basis: rank 7. A directly responsive
  current company FAQ was rank 1, so retrieval remained useful, but Phase 5 must
  explicitly order statutory authority rather than relying on vector rank.
- UAE calendar-day leave evidence: statutory target rank 2 behind a responsive
  current FAQ.

No thresholds, targets, or holdout cases were modified after observing results.

## Defects found by the real run

1. A stale process API key could silently take precedence over `.env`.
2. Authentication failure was wrapped as a generic candidate-build failure.
3. Raw `uv.lock` bytes produced different hashes for LF and CRLF checkouts.

The corrective checkpoint detects conflicting key sources, classifies embedding
authentication separately, preserves underlying availability detail, and hashes
logical UTF-8 lockfile content using canonical LF newlines. These corrections do
not change retrieval ranking, evaluation content, thresholds, corpus, chunks,
models, or index-generation logic.
