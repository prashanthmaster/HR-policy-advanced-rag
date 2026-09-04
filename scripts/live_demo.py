#!/usr/bin/env python3
"""
T-6.7 -- the actual live demo, run in front of an interviewer.

Narrates and executes, in order:
  1. Ask a real question against the CURRENT live index -- the "before"
     answer.
  2. Pause: you edit the relevant document directly in Google Drive.
  3. Poll Drive, re-index whatever changed (T-6.3/T-6.4), print any
     version-event flags (T-6.5).
  4. Ask the SAME question again against the freshly-updated index -- the
     "after" answer -- and show whether it actually changed.
  5. Score the after-answer's live faithfulness and show the refusal-gate
     decision (T-6.6) at the calibrated threshold.

Deliberately a thin orchestration script over pieces already built and
independently proven (T-6.1-T-6.6) -- it contains no new pipeline logic
of its own, on purpose: a demo script inventing its own behaviour would
not be evidence the real system works.

Usage:
    .venv-win\\Scripts\\python.exe scripts\\live_demo.py --query "..." --country UAE

Interactive: pauses on a real input() prompt at Step 2 so you control the
pacing live in front of whoever's watching. Safe to Ctrl-C at any point --
nothing is left half-done that a later run can't recover (mark_seen() is
only ever called after a full successful re-index, per T-6.4/T-6.5).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from drive_sync.auth import get_drive_service  # noqa: E402
from drive_sync.change_detector import detect_changes  # noqa: E402
from drive_sync.reindex import reindex_changed_file  # noqa: E402
from grading.answer_pipeline import answer_query  # noqa: E402
from grading.faithfulness_gate import DEFAULT_FAITHFULNESS_THRESHOLD, apply_faithfulness_gate  # noqa: E402
from grading.ragas_client import score_faithfulness  # noqa: E402
from grading.temporal_reasoner import ServiceFacts  # noqa: E402
from ingestion.embedder import EmbeddingCache, OpenAIEmbedder  # noqa: E402
from ingestion.index_units import build_indexable_units  # noqa: E402
from ingestion.parser import parse_corpus  # noqa: E402
from retrieval.bm25_index import build_bm25_index  # noqa: E402
from retrieval.hybrid_search import HybridRetriever  # noqa: E402
from retrieval.vector_index import VectorIndex  # noqa: E402

load_dotenv()

INDEX_PATH = REPO_ROOT / "build" / "vector_index"


def _build_retriever(embedder):
    """Fresh BM25 (free, always re-parses the corpus dir -- see drive_sync/
    reindex.py's own docstring for why that's deliberate) + a NEW VectorIndex
    opened against the on-disk collection. Called twice per demo run
    (before/after) since the vector collection changes on disk in between."""
    corpus_dir = REPO_ROOT / "corpus"
    chunks = parse_corpus(corpus_dir, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    bm25 = build_bm25_index(units)
    vector = VectorIndex(embedder, path=INDEX_PATH)
    vector.open_existing()
    return HybridRetriever(bm25, vector, units), vector


def _print_answer(label: str, result) -> None:
    print(f"\n--- {label} ---")
    print(f"status: {result.status}")
    if result.status == "ANSWERED":
        print(result.answer.text)
        print(f"cited: {[c.clause_id for c in result.answer.citations]}")
    elif result.status == "NEEDS_CLARIFICATION":
        print(f"needs: {[m.fact for m in result.clarification.missing_facts]}")
    else:
        print(f"reasons: {[r.value for r in result.sufficiency.reasons]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", required=True)
    parser.add_argument("--country", default=None)
    parser.add_argument("--jurisdiction-scope", dest="jurisdiction_scope", default=None)
    parser.add_argument("--service-start-date", dest="service_start_date", default=None,
                         help="YYYY-MM-DD, if the query needs it")
    parser.add_argument("--valuation-date", dest="valuation_date", default=None, help="YYYY-MM-DD")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1
    if not INDEX_PATH.exists():
        print(f"{INDEX_PATH} does not exist. Run scripts/build_vector_index.py --live first.", file=sys.stderr)
        return 1

    facts = ServiceFacts(
        service_start_date=dt.date.fromisoformat(args.service_start_date) if args.service_start_date else None,
        valuation_date=dt.date.fromisoformat(args.valuation_date) if args.valuation_date else None,
    )

    reranker = None
    try:
        from retrieval.reranker import FlashRankReranker
        reranker = FlashRankReranker()
    except Exception as exc:  # noqa: BLE001
        print(f"Proceeding without reranking ({exc})")

    cache = EmbeddingCache(REPO_ROOT / "build" / "embedding_cache.json")
    embedder = OpenAIEmbedder(cache=cache)

    print("=" * 70)
    print("STEP 1 -- asking the question against the CURRENT live index")
    print("=" * 70)
    retriever, vector = _build_retriever(embedder)
    before = answer_query(
        retriever, args.query, country=args.country, jurisdiction_scope=args.jurisdiction_scope,
        as_of_date=facts.valuation_date, facts=facts, reranker=reranker,
    )
    _print_answer("BEFORE", before)
    vector.close()  # release the on-disk lock before reindex_changed_file() opens its own

    print("\n" + "=" * 70)
    print("STEP 2 -- now edit the relevant policy document directly in Google Drive.")
    print("Change a real number, date, or obligation. Let it auto-save (a second or two).")
    print("=" * 70)
    input("Press Enter here once you've made the edit and it's saved... ")

    print("\n" + "=" * 70)
    print("STEP 3 -- polling Drive, re-indexing whatever changed")
    print("=" * 70)
    service = get_drive_service()
    changes = detect_changes(service)
    if not changes:
        print("No changes detected -- did the edit actually save? Re-run this script once it has.")
        return 1
    for c in changes:
        result = reindex_changed_file(c, service)
        print(f"  re-indexed {c.drive_doc_name} ({c.rel_path}) -- {result.unit_count} unit(s)")
        for ev in result.version_events:
            flag = "NEEDS REVIEW" if ev.needs_human_review else "info"
            print(f"    [{flag}] clause {ev.clause_id}: {ev.kind.value}")
            if ev.needs_human_review:
                print(f"      {ev.note}")

    print("\n" + "=" * 70)
    print("STEP 4 -- asking the SAME question again against the freshly-updated index")
    print("=" * 70)
    retriever2, vector2 = _build_retriever(embedder)
    after = answer_query(
        retriever2, args.query, country=args.country, jurisdiction_scope=args.jurisdiction_scope,
        as_of_date=facts.valuation_date, facts=facts, reranker=reranker,
    )
    _print_answer("AFTER", after)

    print("\n" + "=" * 70)
    print("STEP 5 -- live faithfulness gate on the AFTER answer")
    print("=" * 70)
    if after.status == "ANSWERED":
        gated = apply_faithfulness_gate(after, args.query, score_faithfulness, DEFAULT_FAITHFULNESS_THRESHOLD)
        verdict = "REFUSED" if gated.refused_by_faithfulness_gate else "PASSED"
        print(f"faithfulness={gated.faithfulness_score:.3f}  threshold={DEFAULT_FAITHFULNESS_THRESHOLD}  -> {verdict}")
    else:
        print(f"AFTER answer status is {after.status} -- the faithfulness gate only applies to ANSWERED results.")

    vector2.close()

    changed = (before.status != after.status) or (
        before.status == "ANSWERED" and after.status == "ANSWERED" and before.answer.text != after.answer.text
    )
    print("\n" + "=" * 70)
    print(f"RESULT: the answer {'CHANGED' if changed else 'did NOT change'} after the live edit.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
