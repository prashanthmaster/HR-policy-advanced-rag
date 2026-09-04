"""
T-6.4 -- incremental re-index of only the changed document.

Given a ChangedFile (from change_detector.detect_changes()), this:

1. Exports the live Drive doc as plain text.
2. Overwrites the corresponding local corpus/*.md file with it -- so the
   repo stays in sync with what's actually live in Drive, and so the BM25
   index (which is never persisted -- see below) sees the new content the
   next time anything parses the corpus fresh.
3. Re-parses ONLY that one file (ingestion.parser.parse_file), not the
   whole corpus.
4. Builds IndexableUnits for just that file's clauses.
5. Calls VectorIndex.reindex_source_file() -- deletes that file's old
   points, embeds (via the existing cache -- unchanged clauses in this
   file cost nothing extra) and upserts the new ones. Every other
   document's points in the persisted index are untouched.
6. Only on success, calls change_detector.mark_seen() so the next poll
   doesn't report this file again.

Deliberately NOT incremental on the BM25/lexical side: rank_bm25's
BM25Okapi computes corpus-wide document-frequency statistics at
construction time, so there is no meaningful notion of "update just one
document" for it -- and every real script in this project (dump_rerank_
scores.py, run_retrieval_harness.py) already rebuilds BM25Index from a
fresh parse_corpus() call every time it runs, at zero API cost, rather
than loading a persisted one. Since step 2 above already overwrote the
local corpus file, the next thing that builds a BM25 index picks up the
edit automatically, for free -- there is no separate BM25 re-index step
to write. This asymmetry (vector: incremental and persisted; BM25: full
rebuild, cheap, never persisted) is deliberate, not an oversight -- see
PROJECT_PLAN.md Phase 6 Change Log.
"""

from __future__ import annotations

import os
from pathlib import Path

from ingestion.embedder import EmbeddingCache, OpenAIEmbedder
from ingestion.index_units import build_indexable_units
from ingestion.logging_setup import get_logger
from ingestion.parser import parse_file
from retrieval.vector_index import VectorIndex

from drive_sync.change_detector import ChangedFile, export_plain_text, mark_seen

_log = get_logger("drive_sync.reindex")

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_ROOT = REPO_ROOT / "corpus"
VECTOR_INDEX_PATH = REPO_ROOT / "build" / "vector_index"
EMBEDDING_CACHE_PATH = REPO_ROOT / "build" / "embedding_cache.json"


def reindex_changed_file(changed: ChangedFile, service) -> int:
    """Re-index exactly one changed Drive document. Returns the number of
    indexable units (retrieval pieces) written for it. Raises on any
    failure -- callers (scripts/reindex_from_drive.py) should NOT call
    mark_seen() themselves if this raises, so a failed re-index is picked
    up again on the next poll rather than silently skipped."""
    local_path = CORPUS_ROOT / changed.rel_path
    _log.info("re-indexing %s (%s)", changed.drive_doc_name, changed.rel_path)

    # Step 1-2: pull the live text, overwrite the local corpus file.
    new_text = export_plain_text(service, changed.drive_file_id)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(new_text, encoding="utf-8")

    # Step 3-4: re-parse just this file, build its units.
    chunks = parse_file(local_path, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)

    # source_file must match exactly what parse_file/Chunk computed
    # (relative to REPO_ROOT, e.g. "corpus/tier1_law/india/india_law.md")
    # -- NOT changed.rel_path, which is relative to corpus/ instead.
    source_file_key = str(local_path.relative_to(REPO_ROOT))

    # Step 5: incremental vector update.
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY not set -- required to embed the changed document's "
            "clauses. Put it in .env and re-run."
        )
    cache = EmbeddingCache(EMBEDDING_CACHE_PATH)
    embedder = OpenAIEmbedder(cache=cache)
    index = VectorIndex(embedder, path=VECTOR_INDEX_PATH)
    index.reindex_source_file(source_file_key, units)

    # Step 6: only mark as seen once everything above actually succeeded.
    mark_seen(changed)

    _log.info("re-indexed %s: %d unit(s) written", changed.rel_path, len(units))
    return len(units)
