#!/usr/bin/env python3
"""
T-5.5, the real run: a four-class confusion matrix (Finding 3,
docs/FAILURE_MODES.md) plus the over-refusal counter that makes the
guardrail's own failure mode a tracked, first-class defect rather than
an average that can hide it.

Design, matching Finding 3 exactly (no fifth RAGAS metric, no new
scoring scheme -- this changes how the dataset's four labels are
scored, nothing else):
  - Every golden item already carries an expected-behaviour `class`:
    MUST_ANSWER / MUST_REFUSE / MUST_CLARIFY / MUST_FLAG.
  - Every item, run through answer_query(), produces a real `status`:
    ANSWERED / NEEDS_CLARIFICATION / INSUFFICIENT.
  - The mapping from class to the one CORRECT status is:
        MUST_ANSWER  -> ANSWERED
        MUST_CLARIFY -> NEEDS_CLARIFICATION
        MUST_REFUSE  -> INSUFFICIENT
        MUST_FLAG    -> ANSWERED (answerable, but must carry a caveat --
                        see the `flag_note_present` column below; this
                        script does NOT yet check the caveat text itself,
                        only that the system attempted to answer rather
                        than refuse or clarify)
    Any other (class, status) pair is a confusion-matrix miss, and
    over_refusal is specifically MUST_ANSWER items that landed on
    INSUFFICIENT (Finding 3's exact definition: "over-refusal
    (MUST_ANSWER -> refused) is tracked as a first-class defect with
    its own count").

Two known, already-diagnosed items are annotated in the output rather
than silently mixed into "unexplained misses" (see PROJECT_PLAN.md
Phase 5 forward-flag note and slot4_plan_and_conventions.md Convention
16-adjacent items):
  - P-01 and P-17: a documented reranker ranking-order limitation
    (a wrong clause outscores a right one; no relevance floor can fix
    this). If either shows up with a low score anywhere in this run,
    that is the known limitation surfacing, not a new defect.
  - The generic-narrative defect found while diagnosing T-5.3/T-5.4
    (this session): whenever `TemporalWorking`s exist, `generate()`
    only emits `w.narrative` -- a per-class template sentence -- and
    never the underlying clause's own text, for every class except the
    arithmetic path. This is annotated per-item (`narrative_only`) so
    T-5.6's baseline write-up doesn't have to re-derive it.

Usage:
    .venv/bin/python eval/run_confusion_matrix.py
    .venv/bin/python eval/run_confusion_matrix.py --probe-id P-01

Needs OPENAI_API_KEY and an already-built build/vector_index/ (same as
every other Phase 5 script) but should hit the embedding cache for
every already-run golden item -- expect zero or near-zero new API
calls, unlike T-5.3/T-5.4 which need a live judge model.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from grading.answer_pipeline import answer_query  # noqa: E402
from grading.temporal_reasoner import ServiceFacts  # noqa: E402
from ingestion.embedder import EmbeddingCache, OpenAIEmbedder  # noqa: E402
from ingestion.index_units import build_indexable_units  # noqa: E402
from ingestion.logging_setup import get_logger  # noqa: E402
from ingestion.parser import parse_corpus  # noqa: E402
from retrieval.bm25_index import build_bm25_index  # noqa: E402
from retrieval.hybrid_search import HybridRetriever  # noqa: E402
from retrieval.vector_index import VectorIndex  # noqa: E402

_log = get_logger("eval.run_confusion_matrix")

_VALID_COUNTRIES = {"India", "UAE", "Germany", "GLOBAL"}
_KNOWN_RERANK_LIMITATION_PROBES = {"P-01", "P-17"}

_EXPECTED_STATUS_FOR_CLASS = {
    "MUST_ANSWER": "ANSWERED",
    "MUST_CLARIFY": "NEEDS_CLARIFICATION",
    "MUST_REFUSE": "INSUFFICIENT",
    "MUST_FLAG": "ANSWERED",
}

# Matches the generic per-piece narrative template lines TemplateGenerator
# emits for every TemporalWorking that isn't the "no workings at all"
# fallback -- see generation/generator.py / grading/temporal_reasoner.py.
# Used only to flag whether an ANSWERED item's text is purely this
# boilerplate with no computed figure and no raw clause text, not to
# change any behaviour.
_NARRATIVE_TEMPLATE_MARKERS = (
    "governs the entire computation",
    "tagged SEGMENTED_ACCRUAL but carries no amendment pair",
    "is GRANDFATHERED",
    "ELECTIVE: the employee may elect",
)


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
    return raw if raw in _VALID_COUNTRIES else None


def _looks_like_pure_narrative_boilerplate(answer_text: str, computed_amount, computed_days) -> bool:
    """True if the answer has a computed figure (real substance) -- False.
    Otherwise, True only if every non-empty line matches one of the known
    generic template patterns, i.e. no raw clause text and no number ever
    appears. This is a diagnostic flag for T-5.6's write-up, not a metric;
    it does not change status/citations/anything the pipeline returns."""
    if computed_amount is not None or computed_days is not None:
        return False
    lines = [ln for ln in answer_text.splitlines() if ln.strip()]
    if not lines:
        return False
    has_number = bool(re.search(r"\d", " ".join(lines)))
    all_boilerplate = all(any(marker in ln for marker in _NARRATIVE_TEMPLATE_MARKERS) or ln.startswith("Governing version effective from") or ln.startswith("Note:") for ln in lines)
    return all_boilerplate and not has_number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("--probe-id", action="append", dest="probe_ids")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass

    import os
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
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
    if not args.no_rerank:
        try:
            from retrieval.reranker import FlashRankReranker
            reranker = FlashRankReranker()
            print("FlashRank reranker loaded from local cache.")
        except Exception as exc:
            print(f"Proceeding WITHOUT reranking -- FlashRankReranker unavailable ({exc}).")

    per_item = []
    matrix: Counter = Counter()  # (expected_class, actual_status) -> count
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
        expected_class = item.get("class")
        actual_status = result.status
        matrix[(expected_class, actual_status)] += 1

        expected_status = _EXPECTED_STATUS_FOR_CLASS.get(expected_class)
        row = {
            "probe_id": item["probe_id"],
            "expected_class": expected_class,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "class_match": actual_status == expected_status,
            "known_rerank_limitation": item["probe_id"] in _KNOWN_RERANK_LIMITATION_PROBES,
        }
        if actual_status == "ANSWERED" and result.answer is not None:
            row["narrative_only_no_substance"] = _looks_like_pure_narrative_boilerplate(
                result.answer.text, result.answer.computed_amount, result.answer.computed_days,
            )
            row["citation_count"] = len(result.answer.citations)
        per_item.append(row)

    over_refusal = [r for r in per_item if r["expected_class"] == "MUST_ANSWER" and r["actual_status"] == "INSUFFICIENT"]
    total_matches = sum(1 for r in per_item if r["class_match"])
    narrative_only_count = sum(1 for r in per_item if r.get("narrative_only_no_substance"))
    answered_count = sum(1 for r in per_item if r["actual_status"] == "ANSWERED")

    print(f"\nRan {len(items)} golden items through answer_query().")
    print(f"Class match (expected status per Finding 3's mapping vs actual): {total_matches}/{len(items)}")
    print(f"Over-refusal count (MUST_ANSWER -> INSUFFICIENT, Finding 3's first-class defect): {len(over_refusal)}")
    if over_refusal:
        print("  " + ", ".join(r["probe_id"] for r in over_refusal))
    print(f"ANSWERED items with no substantive content in the answer text (no computed figure, no raw clause text -- see T-5.3/T-5.4 root-cause note): {narrative_only_count}/{answered_count}")

    print("\nConfusion matrix (rows = expected class, columns = actual status):")
    statuses = ["ANSWERED", "NEEDS_CLARIFICATION", "INSUFFICIENT"]
    classes = ["MUST_ANSWER", "MUST_CLARIFY", "MUST_REFUSE", "MUST_FLAG"]
    header = "expected \\ actual".ljust(14) + "".join(s.ljust(22) for s in statuses)
    print(header)
    for c in classes:
        row_str = c.ljust(14) + "".join(str(matrix.get((c, s), 0)).ljust(22) for s in statuses)
        print(row_str)

    out_path = REPO_ROOT / "build" / "confusion_matrix_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "total_item_count": len(items),
        "class_match_count": total_matches,
        "over_refusal_count": len(over_refusal),
        "over_refusal_probe_ids": [r["probe_id"] for r in over_refusal],
        "narrative_only_no_substance_count": narrative_only_count,
        "answered_count": answered_count,
        "matrix": {f"{c}|{s}": matrix.get((c, s), 0) for c in classes for s in statuses},
        "per_item": per_item,
    }, indent=2, default=str), encoding="utf-8")
    print(f"\nFull result written to {out_path}. Copy the summary numbers into "
          f"PROJECT_PLAN.md's Results ledger by hand -- this script does not edit the plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
