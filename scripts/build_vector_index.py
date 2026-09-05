#!/usr/bin/env python3
"""
The actual T-2.7 spend step. NOT run by pytest, NOT run by any test file --
this is a deliberate, by-hand action, because this is the first (and so
far only) place in the repo that can spend real OpenAI credit against the
confirmed $4.98 balance.

Usage:
    .venv/bin/python scripts/build_vector_index.py --dry-run
        Embeds a 3-clause slice only, to see one real cost number on the
        OpenAI dashboard before committing to the full corpus. Recommended
        first run, per PROJECT_PLAN.md's Phase 2 gate note.

    .venv/bin/python scripts/build_vector_index.py --live
        Embeds the full 72-clause / 84-unit corpus and writes the index to
        build/vector_index/ (gitignored -- an index is a build artifact,
        not source).

Requires OPENAI_API_KEY to be set (env var, or a .env file loaded by
python-dotenv -- both work since the openai client and load_dotenv() are
called below). Refuses to run at all without a key, rather than silently
doing nothing or crashing deep inside the openai client with a less clear
error.
"""

from __future__ import annotations

import argparse
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

_log = get_logger("scripts.build_vector_index")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="embed only a 3-clause slice, to see one real cost number first")
    mode.add_argument("--live", action="store_true", help="embed the full corpus and write the index")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY is not set. Put it in a .env file at the repo root "
            "(OPENAI_API_KEY=sk-...) or export it, then re-run. Refusing to "
            "proceed without it rather than failing deep inside the client.",
            file=sys.stderr,
        )
        return 1

    # Defensive strip: a value pasted into a CI secret (or a .env line) can
    # silently pick up a trailing newline/space, which the OpenAI/langchain
    # clients then send as-is in the Authorization header -- httpx/h11 reject
    # that with a cryptic "Illegal header value" error (hit for real in
    # GitHub Actions, see PROJECT_PLAN.md Phase 7 Change Log). Stripping once,
    # here, fixes it for every downstream client that reads this env var.
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"].strip()

    corpus_dir = REPO_ROOT / "corpus"
    chunks = parse_corpus(corpus_dir, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)

    if args.dry_run:
        units = units[:3]
        print(f"DRY RUN: embedding {len(units)} unit(s) only. Check the OpenAI dashboard "
              f"afterwards for the real cost of this call before running --live.")

    cache = EmbeddingCache(REPO_ROOT / "build" / "embedding_cache.json")
    embedder = OpenAIEmbedder(cache=cache)

    index_path = REPO_ROOT / "build" / "vector_index"
    index = VectorIndex(embedder, path=None if args.dry_run else index_path)
    index.build(units)

    print(f"Built vector index over {len(units)} unit(s).")
    if args.live:
        print(f"Persisted to {index_path} (gitignored -- rebuild by re-running this script, don't commit it).")
    else:
        print("Dry run only -- nothing persisted. Re-run with --live once you've confirmed the cost.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
