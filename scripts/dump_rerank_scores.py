#!/usr/bin/env python3
"""
Calibration script for retrieval/hybrid_search.py's min_rerank_score fix
(Session 5, reopened Phase 3 -- see PROJECT_PLAN.md's Phase 3 "Reopened"
note and the module docstring on retrieval/hybrid_search.py).

Prints REAL FlashRank rerank_score values, per candidate, for a small
set of representative probe queries -- chosen deliberately to cover both
shapes the floor must get right:
  - genuinely single-topic queries (P-30: housing allowance) where every
    piece except the top one or two should score low and a floor should
    exclude them.
  - genuinely multi-clause queries (P-02, P-3a) where a SECOND piece
    legitimately belongs in the answer (the other half of a
    SEGMENTED_ACCRUAL amendment pair) and must NOT be scored so low that
    a floor would cut it.

Extended 2026-09-04 (Session 9) with four more real cases surfaced by
the first post-narrative-fix confusion-matrix run, all suspected to be
the SAME class of limitation as P-01/P-17 above (a real answer scores
too low, or an unrelated clause scores too high, and no floor value can
fix an ordering problem -- only remove things below a line):
  - P-16: retrieves a near-duplicate "senior grade" notice clause
    alongside the correct "junior grade" one and cites both -- is the
    wrong one scoring high enough to survive, or is there no meaningful
    score gap between the two at all?
  - P-18: the clause that actually answers correctly ("Germany has no
    general severance/gratuity scheme") is found and used; a related,
    less on-topic clause (KSchG's dismissal-protection scope) scores
    too low to be retrieved alongside it. Check whether that's a real
    ordering problem or just a query this second clause was never a
    strong match for.
  - P-28: a colloquial phrasing ("I get nothing since I left before 5
    years... that's illegal, isn't it?") apparently doesn't score well
    against the formal eligibility clause it needs -- check whether the
    real clause is present at all in the raw candidate list, and how
    far down.
  - P-39: a paternity-leave query with no matching content in the
    corpus (a deliberate absence) apparently still scores unrelated
    country-specific leave clauses high enough to look like a real
    match, producing a false "which country" prompt instead of a clean
    "nothing on this" response.

This is a read-only diagnostic -- it does not change retrieve()'s
behaviour or pick a floor itself. Report the printed table back so the
actual min_rerank_score value (and whichever downstream call sites
should pass it) can be chosen from real numbers, not guessed, per this
project's standing rule against unmeasured constants.

Usage:
    .venv-win\\Scripts\\python.exe scripts\\dump_rerank_scores.py
    .venv-win\\Scripts\\python.exe scripts\\dump_rerank_scores.py --probe-id P-30
        Restrict to one probe (cheap -- one query, top_k candidates only).

Requires OPENAI_API_KEY, an already-built build/vector_index/, and the
FlashRank model already prefetched (scripts/prefetch_reranker_model.py) --
same preconditions as scripts/run_retrieval_harness.py.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eval.retrieval_harness import load_expected_clauses, load_probe_queries  # noqa: E402
from eval.run_confusion_matrix import _normalize_country  # noqa: E402
from ingestion.embedder import EmbeddingCache, OpenAIEmbedder  # noqa: E402
from ingestion.index_units import build_indexable_units  # noqa: E402
from ingestion.parser import parse_corpus  # noqa: E402
from retrieval.bm25_index import build_bm25_index  # noqa: E402
from retrieval.hybrid_search import HybridRetriever  # noqa: E402
from retrieval.reranker import FlashRankReranker  # noqa: E402
from retrieval.vector_index import VectorIndex  # noqa: E402

# Deliberately covers both shapes described in the module docstring above.
# Not the whole 43-probe set -- this is a calibration sample, not a re-run
# of T-3.6 (that's scripts/run_retrieval_harness.py's job, separately,
# once a floor value is actually chosen).
DEFAULT_PROBE_IDS = ["P-30", "P-02", "P-3a", "P-01", "P-17", "P-16", "P-18", "P-28", "P-39"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--probe-id", action="append", dest="probe_ids", default=None,
                         help="restrict to one probe id (repeatable); default: a small representative set")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    probe_ids = args.probe_ids or DEFAULT_PROBE_IDS

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

    all_queries = load_probe_queries()
    expected_by_probe = load_expected_clauses()

    # Session 9 fix: this script used to call retriever.retrieve() with NO
    # country/jurisdiction_scope, unlike every real production entry point
    # (grading/answer_pipeline.py's answer_query, eval/run_confusion_matrix.py),
    # which resolve country from the golden set's own "country" field per
    # item and pass it through as a HARD filter (retrieval/filters.py).
    # That meant this script's numbers overstated cross-country noise for
    # any probe that DOES have a resolved country -- P-16 (India), P-18
    # (Germany), P-28 (India) all get the wrong-country candidates removed
    # entirely in the real pipeline; P-39 has no resolved country (None) by
    # design and is unaffected by this fix. Loading real per-probe country
    # here so the calibration numbers match what the pipeline actually sees.
    import json as _json
    _golden = _json.load(open(REPO_ROOT / "eval" / "golden" / "scored_golden_set.json", encoding="utf-8"))
    country_by_probe = {it.get("probe_id"): _normalize_country(it.get("country")) for it in _golden["items"]}
    jurisdiction_by_probe = {it.get("probe_id"): it.get("jurisdiction_scope") for it in _golden["items"]}
    missing = [pid for pid in probe_ids if pid not in all_queries]
    if missing:
        print(f"Unknown probe id(s): {missing}. Known ids come from eval/golden/adversarial_probe_set.md.", file=sys.stderr)
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

    try:
        reranker = FlashRankReranker()
    except Exception as exc:
        print(f"FlashRankReranker unavailable ({exc}). Run scripts/prefetch_reranker_model.py first.", file=sys.stderr)
        return 1

    for probe_id in probe_ids:
        query = all_queries[probe_id]
        expected = set(expected_by_probe.get(probe_id, []))
        results = retriever.retrieve(
            query, top_k=args.top_k, reranker=reranker,
            country=country_by_probe.get(probe_id),
            jurisdiction_scope=jurisdiction_by_probe.get(probe_id),
        )

        print(f"\n=== {probe_id} ===")
        print(f"query: {query}")
        print(f"expected clause_ids ({len(expected)}): {sorted(expected)}")
        print(f"country filter applied: {country_by_probe.get(probe_id)!r}")
        print(f"{'rank':>4}  {'rerank_score':>13}  {'expected?':>9}  clause_id")
        for i, r in enumerate(results, start=1):
            hit = "yes" if r.clause_id in expected else ""
            score = "n/a" if r.rerank_score is None else f"{r.rerank_score:.4f}"
            print(f"{i:>4}  {score:>13}  {hit:>9}  {r.clause_id}")

    print(
        "\nReport this whole output back. Look for: (a) on P-30-shaped single-topic queries, "
        "a clear score gap between the on-topic piece(s) and the rest; (b) on P-02/P-3a-shaped "
        "queries, whether BOTH expected pieces score comfortably above wherever that gap sits. "
        "The floor value is whatever separates (a)'s off-topic tail from (b)'s legitimate second piece."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
