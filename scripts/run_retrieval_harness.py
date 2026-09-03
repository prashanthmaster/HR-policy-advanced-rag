#!/usr/bin/env python3
"""
T-3.6, the real run: Context Precision + Context Recall over the
adversarial probe set, against the REAL persisted vector index (built by
scripts/build_vector_index.py, real OpenAI embeddings) and, optionally,
the real FlashRank reranker (weights prefetched by
scripts/prefetch_reranker_model.py). NOT run by pytest -- pytest's
test_retrieval_harness.py exercises the same harness code mechanically,
with MockEmbedder/no reranker, which proves the metric math and the
probe-parsing are correct but says nothing about real retrieval quality.
This script is what produces the number that goes in PROJECT_PLAN.md's
Results ledger -- per this project's ground rule, no such number may be
quoted anywhere until this script has actually been run and its output
recorded.

Usage:
    .venv/bin/python scripts/run_retrieval_harness.py
        Embeds each probe query with real OpenAI embeddings (queries
        only -- the corpus itself is already embedded in
        build/vector_index) and searches BM25 + the persisted vector
        index. Reranking is used only if the FlashRank model has already
        been prefetched; otherwise the run proceeds without it and says
        so, rather than failing the whole measurement over an optional
        step.

    .venv/bin/python scripts/run_retrieval_harness.py --top-k 5
        Override top_k (default 10).

Requires OPENAI_API_KEY (same .env loading as build_vector_index.py) and
an already-built build/vector_index/ (run build_vector_index.py --live
first).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eval.retrieval_harness import run_retrieval_harness  # noqa: E402
from ingestion.embedder import EmbeddingCache, OpenAIEmbedder  # noqa: E402
from ingestion.index_units import build_indexable_units  # noqa: E402
from ingestion.logging_setup import get_logger  # noqa: E402
from ingestion.parser import parse_corpus  # noqa: E402
from retrieval.bm25_index import build_bm25_index  # noqa: E402
from retrieval.hybrid_search import HybridRetriever  # noqa: E402
from retrieval.vector_index import VectorIndex  # noqa: E402

_log = get_logger("scripts.run_retrieval_harness")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--no-rerank", action="store_true", help="skip FlashRank even if the model is cached")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set. See scripts/build_vector_index.py's usage note.", file=sys.stderr)
        return 1

    index_path = REPO_ROOT / "build" / "vector_index"
    if not index_path.exists():
        print(f"{index_path} does not exist yet. Run scripts/build_vector_index.py --live first.", file=sys.stderr)
        return 1

    corpus_dir = REPO_ROOT / "corpus"
    chunks = parse_corpus(corpus_dir, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)

    bm25 = build_bm25_index(units)

    cache = EmbeddingCache(REPO_ROOT / "build" / "embedding_cache.json")
    embedder = OpenAIEmbedder(cache=cache)
    vector = VectorIndex(embedder, path=index_path)
    vector.open_existing()

    retriever = HybridRetriever(bm25, vector, units)

    reranker = None
    if not args.no_rerank:
        try:
            from retrieval.reranker import FlashRankReranker
            reranker = FlashRankReranker()
            print("FlashRank reranker loaded from local cache.")
        except Exception as exc:  # model not prefetched, or any other rerank-init failure
            print(f"Proceeding WITHOUT reranking -- FlashRankReranker unavailable ({exc}). "
                  f"Run scripts/prefetch_reranker_model.py once to enable it.")

    report = run_retrieval_harness(retriever, top_k=args.top_k, reranker=reranker)

    print(f"\nScored {report.scored_probe_count} probes "
          f"(excluded {len(report.excluded_probe_ids)}: {', '.join(report.excluded_probe_ids)})")
    print(f"Mean Context Precision@{args.top_k}: {report.mean_precision:.3f}")
    print(f"Mean Context Recall@{args.top_k}:    {report.mean_recall:.3f}")
    print(f"Reranked: {reranker is not None}")

    out_path = REPO_ROOT / "build" / "retrieval_harness_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "top_k": args.top_k,
                "reranked": reranker is not None,
                "scored_probe_count": report.scored_probe_count,
                "excluded_probe_ids": report.excluded_probe_ids,
                "mean_precision": report.mean_precision,
                "mean_recall": report.mean_recall,
                "per_probe": [
                    {
                        "probe_id": r.probe_id,
                        "expected": r.expected,
                        "retrieved_clause_ids": r.retrieved_clause_ids,
                        "precision": r.precision,
                        "recall": r.recall,
                    }
                    for r in report.per_probe
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nFull result written to {out_path}. Copy the summary numbers into "
          f"PROJECT_PLAN.md's Results ledger by hand -- this script does not edit the plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
