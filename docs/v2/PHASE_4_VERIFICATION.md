# Phase 4 verification: measured version-aware hybrid retrieval

- Status: **LOCAL ACCEPTED — closing GitHub Actions run pending**
- Release evaluated commit: `01d93a8cd3863cca4a8c34be4b8a5e7a976c0149`
- Release execution date: 2026-09-06
- Frozen case-set SHA-256:
  `06d931aec5fcba2b3c6b1f2b33a193397796de4574ae252bfb8198221a76b555`
- Canonical LF release artifact SHA-256:
  `59e9c43c0edcb2e5c8498df48acc57457b3bd6b96ae66d808e08a62e7cd116b1`
- Original Windows CRLF transport SHA-256:
  `b4d4cd1cb06aa337271e3ab16540f350e08418014e373f8dcf8eae53a1030973`

The release exam was executed once after the development corrective checkpoint.
No retrieval cases, target groups, thresholds, corpus sources, chunks, models,
or ranking logic changed after observing the release results.

## Release configuration

- 36 frozen cases: 12 development, 12 regression, 12 holdout.
- 126 deterministic chunks in one in-memory Qdrant candidate collection.
- Dense vectors: OpenAI `text-embedding-3-small`, 1,536 dimensions.
- Sparse vectors: FastEmbed `Qdrant/bm25`.
- Fusion: Qdrant reciprocal rank fusion.
- Embedding tokens: 22,538.
- Corpus generation:
  `india-uae-policy-portfolio-2026-09-06-v1`.
- Corpus SHA-256:
  `43f5fbfa14e696713334dab1420b1a3bd5984dfbf241d5f4feda3a4d1f5edb2c`.
- Index generation:
  `e70437db8c387b53df7b3e6d7158ab13c04ab5c59a533a2a3c9aed4618ab30a2`.

## Independently recomputed results

| Population | Cases | Recall@10 | MRR@10 | Temporal accuracy | Leakage | Errors | Exclusions |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full release exam | 36 | 1.0000 | 0.9484 | 1.0000 | 0 | 0 | 0 |
| Untouched holdout | 12 | 1.0000 | 0.9583 | 1.0000 | 0 | 0 | 0 |

All six jurisdiction/topic slices achieved Recall@10 of 1.00. Full-exam slice
MRR was:

| Slice | Cases | MRR@10 |
|---|---:|---:|
| India gratuity | 6 | 0.8571 |
| India leave | 6 | 1.0000 |
| India notice | 6 | 1.0000 |
| UAE gratuity | 6 | 0.9167 |
| UAE leave | 6 | 0.9167 |
| UAE notice | 6 | 1.0000 |

Eleven of twelve holdout targets were ranked first. The remaining UAE gratuity
statutory target ranked second behind the applicable current company policy,
which is a reasonable retrieval ordering. Phase 5 must still apply explicit
legal-authority and policy-precedence rules; vector rank is not a legal decision.

## Evidence-integrity checks

The checked-in development and release artifacts now load through a strict,
immutable Pydantic contract. Tests independently recompute:

- every case's required-source recall and reciprocal rank;
- forbidden-version temporal correctness;
- jurisdiction, topic, and effective-date leakage;
- full aggregates and every jurisdiction/topic slice;
- the isolated holdout aggregate;
- the frozen case-set and canonical artifact identities.

The contract rejects duplicate splits, inconsistent row counts, duplicate case
IDs, and a `passed` value that contradicts the frozen thresholds.

Two non-material ordering differences appeared between repeated development
queries in the development and release runs. One changed only rank 10; the
other swapped ranks 7 and 8. Neither changed a required target's rank, any case
score, any aggregate, or any gate. These are recorded as low-rank tie/order
variation rather than hidden as byte-for-byte stability.

## Claim boundary

Phase 4 proves that the retrieval layer performs strongly when country, topic,
and as-of date are already supplied as structured facts. It does **not** prove:

- that free-text questions yield the correct facts;
- that statutory and company-policy authority is resolved correctly;
- that benefit calculations are correct;
- that an LLM answer is faithful, concise, or safe;
- that the service is production-ready or legally reviewed.

Phase 5 owns deterministic temporal/authority decisions, missing-fact handling,
and benefit calculations. Phase 6 will add structured LLM explanation only after
those decisions are proven independently.
