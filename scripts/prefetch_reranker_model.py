#!/usr/bin/env python3
"""
One-time FlashRank model download. NOT run by pytest.

Why this exists as its own script: FlashRank's Ranker() downloads its
model weights from huggingface.co on first construction, and that host is
blocked by this project's sandbox network policy in both the cloud
container and the device-bridge shell (identical block hit T-2.7's
OpenAI calls -- see slot4_progress.md). This script must be run once from
a plain terminal on Prashanth's own machine, outside any sandbox proxy.
After it succeeds, the cached weights are reused by every later
FlashRankReranker() call (including scripts/run_retrieval_harness.py) --
no further network needed.

Usage:
    .venv/bin/python scripts/prefetch_reranker_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from retrieval.reranker import DEFAULT_CACHE_DIR, RERANK_MODEL  # noqa: E402


def main() -> int:
    print(f"Downloading FlashRank model {RERANK_MODEL!r} to {DEFAULT_CACHE_DIR} ...")
    try:
        from flashrank import Ranker
    except ImportError:
        print("flashrank is not installed. Run: uv pip install -r requirements.txt", file=sys.stderr)
        return 1

    Ranker(model_name=RERANK_MODEL, cache_dir=str(DEFAULT_CACHE_DIR))
    print("Model cached. retrieval.reranker.FlashRankReranker() will now work offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
