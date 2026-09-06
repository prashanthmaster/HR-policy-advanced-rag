# ADR-0005: One version-aware hybrid retrieval index

- Status: accepted for Phase 4A candidate
- Date: 2026-09-06

## Context

V1 maintained independent BM25 and dense stores and fused their results in
application code. The stores could represent different corpus generations, and
failures could silently downgrade retrieval. It also reused a repeatedly tuned
question set as quality evidence.

Phase 3 produces 126 deterministic chunks from one certified corpus generation.
Phase 4 must retrieve them without losing jurisdiction, topic, effective-date,
or generation boundaries.

## Decision

Use one Qdrant collection containing named dense and sparse vectors:

- dense: OpenAI `text-embedding-3-small`, 1,536 dimensions;
- sparse: `Qdrant/bm25` through Qdrant-supported FastEmbed;
- fusion: Qdrant reciprocal-rank fusion (RRF);
- filters: exact corpus generation, jurisdiction (`requested` or `GLOBAL`),
  topic, `effective_from <= as_of`, and `effective_to > as_of` or absent;
- publication: immutable candidate collection now; alias promotion is Phase 8.

The sparse encoder runs client-side for reproducible local and CI use. Sparse
vectors live in Qdrant beside dense vectors; there is no second BM25 store and
no custom fusion implementation.

Qdrant `v1.19.1` is pinned for the CI server contract and `qdrant-client`
`v1.19.x` is locked. Application code uses `query_points`, named-vector
prefetches, and Qdrant RRF.

## Evaluation contract

The retrieval exam was frozen before implementation:

- 36 unique cases;
- 12 development, 12 regression, 12 holdout;
- exactly two cases per split × jurisdiction × topic;
- targets reference stable source IDs, not generated chunk IDs;
- case SHA-256: `06d931aec5fcba2b3c6b1f2b33a193397796de4574ae252bfb8198221a76b555`.

Frozen release gates:

- overall source-group Recall@10 >= 0.90;
- each jurisdiction/topic slice Recall@10 >= 0.85;
- mean reciprocal rank@10 >= 0.75;
- temporal-version accuracy = 1.00;
- filter leakage = 0;
- errors = 0 and exclusions = 0.

Development mode runs only development and regression cases. Release mode adds
the frozen holdout. Holdout failures cannot be repaired by changing a question,
target, or threshold; they require root-cause analysis and a new explicitly
versioned evaluation cycle.

## Failure behavior

- Missing country, topic, or as-of date fails before provider access.
- Existing candidate collection names cannot be overwritten.
- Encoder cardinality and vector dimensions are validated.
- Qdrant or embedding failure becomes `RetrievalUnavailableError`.
- Missing or cross-generation payload becomes `RetrievalIntegrityError`.
- No dependency failure becomes an ordinary empty result.

For local evaluation, `OPENAI_API_KEY` may be loaded from a repository-root
`.env` file. `.env` and `*.env` are excluded from Git and Docker; only
`.env.example` with a non-secret placeholder is tracked. CI and deployment use
process or secret-manager environment injection.

## Primary references

- Qdrant hybrid queries and RRF:
  https://qdrant.tech/documentation/concepts/hybrid-queries/
- Qdrant FastEmbed integration:
  https://qdrant.tech/documentation/fastembed/
- OpenAI embeddings guide:
  https://developers.openai.com/api/docs/guides/embeddings

## Consequences

The system has one retrieval state and can test amendments without relying on
the LLM. Dense embeddings still provide semantic matching; controlled LLM answer
generation arrives in Phase 6. Phase 4 is not complete until a real development
run and a single release holdout run pass the frozen gates.
