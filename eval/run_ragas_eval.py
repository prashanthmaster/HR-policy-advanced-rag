#!/usr/bin/env python3
"""
T-5.3, the real run: RAGAS Context Precision, Context Recall, Faithfulness,
and Answer Correctness over eval/golden/scored_golden_set.json, against the
REAL persisted vector index and REAL answer_query() pipeline -- not mocked.
Same reason as scripts/run_retrieval_harness.py and scripts/build_vector_index.py:
this project's standing rule is that no performance number may be quoted
anywhere until it comes from a real run recorded here, and RAGAS's judge
metrics need real OpenAI calls (gpt-4o-mini for the judge LLM,
text-embedding-3-small for the embeddings RAGAS itself needs) that this
sandbox's network block prevents Claude from making directly. Run this
yourself, from a plain terminal, outside any sandbox.

Scope note carried over from M4 (see grading/answer_pipeline.py's own
docstring): answer_query() takes country/jurisdiction_scope/ServiceFacts as
CALLER-SUPPLIED arguments, not parsed from the query text. So this script
reads a "facts" object out of each golden item (added in Session 5,
commit fe9e305, for P-01/P-02/P-03 so far) and passes it straight into
ServiceFacts(...) -- it does not attempt to extract dates from the query
string itself. Items without a "facts" block run with ServiceFacts()
(all-None), same as any caller that hasn't resolved those facts yet.

Known limitation on `country`, stated plainly: the golden set's `country`
field is free-text description for a human reader ("UAE-DIFC", "UAE
(entity-dependent)"), not the strict {"India","UAE","Germany","GLOBAL"}
enum ingestion/schema.py's IndexableUnit.country actually validates
against -- passing a value like "UAE-DIFC" straight into answer_query()'s
hard country filter would silently match nothing and produce a bogus
INSUFFICIENT. _normalize_country() below maps anything outside the four
real values to None (no hard country filter) rather than mis-filtering.

The DIFC-vs-mainland split itself is NOT a gap, though -- retrieval already
has a purpose-built `jurisdiction_scope` filter (retrieval/filters.py,
Phase 3) with fallback semantics (a clause tagged neither mainland nor
DIFC matches either query), and the corpus already tags every UAE clause
uae-mainland/uae-difc. This script reads a per-item `jurisdiction_scope`
field (added Session 5) and passes it straight through. It is set only
where the query is actually unambiguous about entity (P-3a). It is
deliberately left unset for P-3b/P-17 -- those two probes' entire point is
that the query names a LOCATION ("Dubai" / "the DIFC office") rather than
the employing entity, and their golden answers require citing BOTH regimes
and flagging that entity (not location) governs; hard-filtering either one
to a single jurisdiction would silently resolve the ambiguity the probe
exists to catch.

Only items whose real pipeline run reaches ANSWERED are scored by RAGAS --
Context Precision/Recall/Faithfulness/Answer Correctness are defined over
a (question, answer, contexts, reference) tuple and don't mean anything for
a NEEDS_CLARIFICATION or INSUFFICIENT result. Those are recorded in the
output (status, and whether it matched the golden item's expected `class`)
for T-5.5's confusion matrix to consume separately -- this script does not
compute the confusion matrix itself.

Usage:
    .venv/bin/python eval/run_ragas_eval.py
        Runs every golden item through the real pipeline, scores the
        ANSWERED ones with RAGAS, writes build/ragas_eval_result.json.

    .venv/bin/python eval/run_ragas_eval.py --probe-id P-01
        Restrict to one golden item (repeatable) -- useful for a quick
        check before committing to a full (paid) run.

Requires OPENAI_API_KEY (same .env loading as build_vector_index.py), an
already-built build/vector_index/ (run scripts/build_vector_index.py --live
first), and `pip install ragas datasets langchain-openai` (ragas/datasets
are already in requirements.txt; langchain-openai is ragas's LLM/embeddings
wrapper and may need adding if not already present -- this script fails
fast with a clear message if it's missing rather than a confusing traceback).
"""

from __future__ import annotations

import argparse
import datetime as dt
import inspect
import json
import os
import sys
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

_log = get_logger("eval.run_ragas_eval")

JUDGE_MODEL = "gpt-4o-mini"  # locked budget model, PROJECT_PLAN.md Phase 2 gate note
EMBEDDING_MODEL = "text-embedding-3-small"


def _parse_date(s: str | None) -> dt.date | None:
    return dt.date.fromisoformat(s) if s else None


def _facts_from_item(item: dict) -> ServiceFacts:
    facts = item.get("facts") or {}
    return ServiceFacts(
        service_start_date=_parse_date(facts.get("service_start_date")),
        valuation_date=_parse_date(facts.get("valuation_date")),
        monthly_wage=facts.get("monthly_wage"),
    )


_VALID_COUNTRIES = {"India", "UAE", "Germany", "GLOBAL"}


def _normalize_country(raw: str | None) -> str | None:
    """See the module docstring's "Known limitation" note. Golden-set
    `country` is free text for a human reader; only pass it through as a
    hard filter when it's one of the four values the corpus schema
    actually uses, else don't filter (None) rather than mis-filter."""
    return raw if raw in _VALID_COUNTRIES else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("--probe-id", action="append", dest="probe_ids",
                         help="Restrict to this probe_id (repeatable). Default: all items.")
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

    try:
        # Neutralize nest_asyncio.apply() BEFORE importing ragas. Root cause
        # (confirmed 2026-09-04 by reading the installed source of both
        # versions, not guessed from the traceback): ragas 0.3.1 -- what
        # Prashanth's .venv-win actually installed, an OLDER release than
        # this project's 0.4.3 dev-reference venv, not a newer one as first
        # assumed -- calls nest_asyncio.apply() unconditionally at MODULE
        # IMPORT TIME in ragas/executor.py, with no guard. ragas 0.4.3 added
        # a guard (ragas/async_utils.py::apply_nest_asyncio) that only
        # applies it when an event loop is ALREADY running (the Jupyter
        # case nest_asyncio exists for) and is a no-op otherwise, which is
        # why 0.4.3 never hit this. nest_asyncio's global loop patching is
        # incompatible with Python 3.11+'s asyncio.timeout() task tracking,
        # and produced "RuntimeError(Timeout should be used inside a task)"
        # on every single job, silently NaN-ing every metric (reproduced on
        # Prashanth's real run, 2026-09-04). Since this script is always a
        # plain top-level script -- never a Jupyter cell with an
        # already-running loop -- nest_asyncio is never actually needed
        # here, on ANY ragas version, so making nest_asyncio.apply() a
        # no-op is safe and makes every version behave like 0.4.3's own
        # guarded default.
        try:
            import nest_asyncio as _nest_asyncio_module
            _nest_asyncio_module.apply = lambda *a, **k: None
        except ImportError:
            pass  # not installed -- fine, nothing to neutralize

        from ragas import EvaluationDataset, SingleTurnSample, evaluate
        from ragas.metrics import answer_correctness, context_precision, context_recall, faithfulness
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    except ImportError as exc:
        print(f"Missing a RAGAS/langchain-openai dependency ({exc}). "
              f"Run: .venv/bin/python -m pip install ragas datasets langchain-openai", file=sys.stderr)
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
    samples = []
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
        row = {
            "probe_id": item["probe_id"],
            "expected_class": item["class"],
            "status": result.status,
            "class_match": (result.status == "ANSWERED" and item["class"] == "MUST_ANSWER")
                or (result.status == "NEEDS_CLARIFICATION" and item["class"] == "MUST_CLARIFY")
                or (result.status == "INSUFFICIENT" and item["class"] in ("MUST_REFUSE", "MUST_FLAG")),
        }
        if result.status == "ANSWERED":
            contexts = [p.text for p in (result.pieces or [])]
            row["answer_text"] = result.answer.text
            row["computed_amount"] = result.answer.computed_amount
            row["computed_days"] = result.answer.computed_days
            expected_computation = item.get("expected_computation") or {}
            row["expected_amount"] = expected_computation.get("computed_amount")
            row["expected_days"] = expected_computation.get("computed_days")
            samples.append(SingleTurnSample(
                user_input=item["query"],
                response=result.answer.text,
                retrieved_contexts=contexts or [""],
                reference=item["golden_answer"],
            ))
            row["ragas_sample_index"] = len(samples) - 1
        else:
            row["answer_text"] = None
            row["ragas_sample_index"] = None
        per_item.append(row)

    print(f"\nRan {len(items)} golden items through answer_query(). "
          f"{sum(1 for r in per_item if r['status'] == 'ANSWERED')} reached ANSWERED and will be RAGAS-scored; "
          f"the rest (NEEDS_CLARIFICATION/INSUFFICIENT) are recorded for T-5.5's confusion matrix only.")

    ragas_scores = {}
    if samples:
        llm = ChatOpenAI(model=JUDGE_MODEL, temperature=0)
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        dataset = EvaluationDataset(samples=samples)
        evaluate_kwargs = dict(
            metrics=[context_precision, context_recall, faithfulness, answer_correctness],
            llm=llm,
            embeddings=embeddings,
        )
        # The nest_asyncio.apply() monkeypatch above (see the comment where
        # ragas is imported) is the actual fix for the "Timeout should be
        # used inside a task" crash. This still passes allow_nest_asyncio=False
        # when the installed ragas version happens to expose that kwarg
        # (0.4.3 and similar) -- redundant with the monkeypatch, but cheap
        # insurance, and it keeps this script correct against whichever
        # ragas release requirements.txt's unversioned pin resolves to.
        ragas_version = getattr(__import__("ragas"), "__version__", "unknown")
        if "allow_nest_asyncio" in inspect.signature(evaluate).parameters:
            evaluate_kwargs["allow_nest_asyncio"] = False
            print(f"(ragas {ragas_version}: passing allow_nest_asyncio=False; "
                  f"nest_asyncio.apply() is also neutralized directly)")
        else:
            print(f"(ragas {ragas_version}: no allow_nest_asyncio parameter on this "
                  f"version's evaluate() -- relying on the nest_asyncio.apply() "
                  f"monkeypatch instead. If metrics still come back as n/a/NaN, "
                  f"the incompatibility has resurfaced somewhere the monkeypatch "
                  f"doesn't reach and needs a fresh look.)")
        eval_result = evaluate(dataset, **evaluate_kwargs)
        result_df = eval_result.to_pandas()
        for idx, row in enumerate(per_item):
            if row["ragas_sample_index"] is not None:
                r = result_df.iloc[row["ragas_sample_index"]]
                row["context_precision"] = float(r.get("context_precision", float("nan")))
                row["context_recall"] = float(r.get("context_recall", float("nan")))
                row["faithfulness"] = float(r.get("faithfulness", float("nan")))
                row["answer_correctness"] = float(r.get("answer_correctness", float("nan")))
        for metric_name in ("context_precision", "context_recall", "faithfulness", "answer_correctness"):
            vals = [row[metric_name] for row in per_item if metric_name in row and row[metric_name] == row[metric_name]]
            ragas_scores[f"mean_{metric_name}"] = sum(vals) / len(vals) if vals else None
    else:
        print("No item reached ANSWERED -- nothing for RAGAS to score. Check the pipeline/facts wiring.",
              file=sys.stderr)

    print("\nRAGAS means (over ANSWERED items only):")
    for k, v in ragas_scores.items():
        print(f"  {k}: {v:.3f}" if v is not None else f"  {k}: n/a")

    class_matches = sum(1 for r in per_item if r["class_match"])
    print(f"\nClass match (actual pipeline status vs. golden `class`): {class_matches}/{len(per_item)} "
          f"-- NOT the confusion matrix itself (T-5.5), just a quick sanity count.")

    out_path = REPO_ROOT / "build" / "ragas_eval_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "judge_model": JUDGE_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "top_k": args.top_k,
        "reranked": reranker is not None,
        "scored_item_count": len(samples),
        "total_item_count": len(items),
        "ragas_means": ragas_scores,
        "per_item": per_item,
    }, indent=2, default=str), encoding="utf-8")
    print(f"\nFull result written to {out_path}. Copy the summary numbers into "
          f"PROJECT_PLAN.md's Results ledger by hand -- this script does not edit the plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
