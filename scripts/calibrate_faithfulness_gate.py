#!/usr/bin/env python3
"""
T-6.6, the real calibration run: what faithfulness threshold should the
live refusal gate use?

Same discipline as Session 6's min_rerank_score calibration (Convention 14
in slot4_plan_and_conventions.md): this script does NOT pick a threshold.
It runs every golden item through the real answer_query() pipeline, and
for every item that reaches ANSWERED, computes its REAL live faithfulness
score (grading.ragas_client.score_faithfulness -- a real OpenAI call per
ANSWERED item, same judge model as Phase 5's batch eval). It then reports,
for a range of candidate thresholds, how many of those items would be
WRONGLY refused (over-refusal) if the gate used that threshold -- the
exact question Risk RK-2 exists to keep in view: a guardrail calibrated
in isolation, without watching its own over-refusal cost, quietly becomes
a refuse-everything machine.

Honest limitation, stated plainly rather than glossed over: this corpus's
golden set has no items deliberately marked "reaches ANSWERED but the
generated answer is actually unfaithful" -- Phase 4/5's generator is
citation-grounded by construction (T-4.4's TemplateGenerator reuses real
clause text, never free-form LLM prose), so there is no confirmed-bad-
faithfulness case to check the gate's TRUE POSITIVE catch rate against.
This script can only speak to the over-refusal (false positive) side of
the threshold choice -- picking a threshold from this data protects
against the gate being too aggressive, not proof it would catch a real
future hallucination. That asymmetry should be stated plainly if this
comes up in an interview, not smoothed over.

Usage:
    .venv-win\\Scripts\\python.exe scripts\\calibrate_faithfulness_gate.py
    .venv-win\\Scripts\\python.exe scripts\\calibrate_faithfulness_gate.py --probe-id P-01

Requires OPENAI_API_KEY and an already-built build/vector_index/ (same as
every other Phase 5/6 real-API script). Costs one real OpenAI call per
ANSWERED golden item (gpt-4o-mini judge) -- comparable to a single T-5.3
run, not the full 4-metric RAGAS batch.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from grading.answer_pipeline import answer_query  # noqa: E402
from grading.ragas_client import score_faithfulness  # noqa: E402
from grading.temporal_reasoner import ServiceFacts  # noqa: E402
from ingestion.embedder import EmbeddingCache, OpenAIEmbedder  # noqa: E402
from ingestion.index_units import build_indexable_units  # noqa: E402
from ingestion.logging_setup import get_logger  # noqa: E402
from ingestion.parser import parse_corpus  # noqa: E402
from retrieval.bm25_index import build_bm25_index  # noqa: E402
from retrieval.hybrid_search import HybridRetriever  # noqa: E402
from retrieval.vector_index import VectorIndex  # noqa: E402

_log = get_logger("scripts.calibrate_faithfulness_gate")

_VALID_COUNTRIES = {"India", "UAE", "Germany", "GLOBAL"}
_CANDIDATE_THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def _parse_date(s: str | None) -> dt.date | None:
    return dt.date.fromisoformat(s) if s else None


def _facts_from_item(item: dict) -> ServiceFacts:
    facts = item.get("facts") or {}
    return ServiceFacts(
        service_start_date=_parse_date(facts.get("service_start_date")),
        valuation_date=_parse_date(facts.get("valuation_date")),
        monthly_wage=facts.get("monthly_wage"),
    )


def _normalize_country(raw: str | None) -> str | None:
    # See eval/run_ragas_eval.py's own docstring for why -- same
    # golden-set free-text-vs-strict-enum mismatch applies here.
    return raw if raw in _VALID_COUNTRIES else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--probe-id", action="append", dest="probe_ids",
                         help="Restrict to this probe_id (repeatable). Default: all items.")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set. See scripts/build_vector_index.py's usage note.", file=sys.stderr)
        return 1

    # Defensive strip: a value pasted into a CI secret (or a .env line) can
    # silently pick up a trailing newline/space, which the OpenAI/langchain
    # clients then send as-is in the Authorization header -- httpx/h11 reject
    # that with a cryptic "Illegal header value" error (hit for real in
    # GitHub Actions, see PROJECT_PLAN.md Phase 7 Change Log). Stripping once,
    # here, fixes it for every downstream client that reads this env var.
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"].strip()

    index_path = REPO_ROOT / "build" / "vector_index"
    if not index_path.exists():
        print(f"{index_path} does not exist yet. Run scripts/build_vector_index.py --live first.", file=sys.stderr)
        return 1

    golden_path = REPO_ROOT / "eval" / "golden" / "scored_golden_set.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    items = golden["items"]
    if args.probe_ids:
        wanted = set(args.probe_ids)
        items = [it for it in items if it["probe_id"] in wanted]
        if not items:
            print(f"No golden items matched --probe-id {sorted(wanted)}", file=sys.stderr)
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
    try:
        from retrieval.reranker import FlashRankReranker
        reranker = FlashRankReranker()
        print("FlashRank reranker loaded from local cache.")
    except Exception as exc:
        print(f"Proceeding WITHOUT reranking -- FlashRankReranker unavailable ({exc}).")

    rows = []
    for item in items:
        facts = _facts_from_item(item)
        result = answer_query(
            retriever, item["query"],
            country=_normalize_country(item.get("country")),
            jurisdiction_scope=item.get("jurisdiction_scope"),
            as_of_date=facts.valuation_date,
            facts=facts,
            reranker=reranker,
            top_k=args.top_k,
        )
        if result.status != "ANSWERED":
            continue

        contexts = [p.text for p in (result.pieces or [])]
        score = score_faithfulness(item["query"], result.answer.text, contexts)
        rows.append({
            "probe_id": item["probe_id"],
            "expected_class": item["class"],
            "faithfulness": score,
        })
        print(f"  {item['probe_id']} ({item['class']}): faithfulness={score:.3f}")

    if not rows:
        print("No item reached ANSWERED -- nothing to calibrate against.", file=sys.stderr)
        return 1

    print(f"\n{len(rows)} ANSWERED item(s) scored. Threshold sweep -- over-refusal cost only "
          f"(see this script's docstring for why this can't measure the true-positive catch rate):\n")
    print(f"{'threshold':>10} | {'would refuse':>12} | {'of which MUST_ANSWER/MUST_FLAG (over-refusal)':>46}")
    print("-" * 75)
    for t in _CANDIDATE_THRESHOLDS:
        would_refuse = [r for r in rows if r["faithfulness"] < t]
        over_refusal = [r for r in would_refuse if r["expected_class"] in ("MUST_ANSWER", "MUST_FLAG")]
        print(f"{t:>10.2f} | {len(would_refuse):>12} | {len(over_refusal):>46}")

    out_path = REPO_ROOT / "build" / "faithfulness_calibration_result.json"
    out_path.write_text(json.dumps({
        "judge_model": "gpt-4o-mini",
        "candidate_thresholds": _CANDIDATE_THRESHOLDS,
        "scored_items": rows,
    }, indent=2), encoding="utf-8")
    print(f"\nFull per-item scores written to {out_path}. Pick a threshold from the table above "
          f"(lowest over-refusal count you're comfortable with) and set grading.faithfulness_gate."
          f"DEFAULT_FAITHFULNESS_THRESHOLD to it by hand -- this script does not choose or write it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
