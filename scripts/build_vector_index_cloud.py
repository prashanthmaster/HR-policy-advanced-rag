#!/usr/bin/env python3
"""
T-8.2: embed the full corpus and upsert it into a real Qdrant Cloud
cluster, instead of the local on-disk collection scripts/build_vector_index.py
writes to build/vector_index/.

Why a separate script rather than a flag on build_vector_index.py: that
script's whole point (per its own docstring) is "the first place in the
repo that can spend real OpenAI credit" -- deliberately narrow and hand-run.
This script reuses its exact corpus-parsing/embedding logic (same
EmbeddingCache, so clause text already embedded for the local build is
NOT re-billed) but targets retrieval.vector_index.VectorIndex's new
url=/api_key= remote mode (added for T-8.2) instead of path=.

This is the ONE-TIME (or "re-run after a real corpus edit") step that
makes Qdrant Cloud have anything to answer with -- Cloud Run itself never
runs this script; the deployed container only ever calls VectorIndex in
read/search mode against the cluster this script populates.

Usage (run on Prashanth's own machine, real network required):
    .venv-win\\Scripts\\python.exe scripts\\build_vector_index_cloud.py

Requires in .env (or exported):
    OPENAI_API_KEY   -- to embed the corpus (cached embeddings are reused,
                         so a re-run after the first costs ~$0)
    QDRANT_URL       -- e.g. https://xxxxxxxx.us-east4-0.gcp.cloud.qdrant.io:6333
    QDRANT_API_KEY   -- from the Qdrant Cloud cluster's API key page

Refuses to run without all three, rather than failing deep inside the
qdrant_client with a less clear connection error.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ingestion.embedder import EmbeddingCache, OpenAIEmbedder  # noqa: E402
from ingestion.index_units import build_indexable_units  # noqa: E402
from ingestion.logging_setup import get_logger  # noqa: E402
from ingestion.parser import parse_corpus  # noqa: E402
from retrieval.vector_index import VectorIndex  # noqa: E402

_log = get_logger("scripts.build_vector_index_cloud")


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass

    missing = [name for name in ("OPENAI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY") if not os.environ.get(name)]
    if missing:
        print(
            f"Missing required env var(s): {', '.join(missing)}. Set them in .env at the "
            "repo root, then re-run. Refusing to proceed without them rather than failing "
            "deep inside the OpenAI/Qdrant clients.",
            file=sys.stderr,
        )
        return 1

    # Same defensive strip as build_vector_index.py / live_demo.py -- a
    # secret pasted with a trailing newline/space breaks the Authorization
    # header (see PROJECT_PLAN.md Phase 7 Change Log for where this bit
    # first, in CI).
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"].strip()
    qdrant_url = os.environ["QDRANT_URL"].strip()
    qdrant_api_key = os.environ["QDRANT_API_KEY"].strip()

    corpus_dir = REPO_ROOT / "corpus"
    chunks = parse_corpus(corpus_dir, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    print(f"Parsed {len(units)} indexable unit(s) from {corpus_dir}.")

    # Same embedding cache as the local build -- clause text already
    # embedded for build/vector_index/ is reused here at zero additional
    # OpenAI cost; only genuinely new/changed text gets billed.
    cache = EmbeddingCache(REPO_ROOT / "build" / "embedding_cache.json")
    embedder = OpenAIEmbedder(cache=cache)

    print(f"Connecting to Qdrant Cloud at {qdrant_url} ...")
    index = VectorIndex(embedder, url=qdrant_url, api_key=qdrant_api_key)
    index.build(units)
    index.close()

    print(f"Built and upserted {len(units)} unit(s) into the 'hrpolicy_clauses' collection on Qdrant Cloud.")
    print("Re-run this script any time the corpus changes and the deployed app needs the update.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
