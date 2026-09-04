#!/usr/bin/env python3
"""
T-5.4, the real run: a custom Citation Accuracy metric, LLM-as-judge,
G-Eval pattern (same shape as the FinGuard-MCP project's judge: a
structured rubric prompt, one JSON verdict per item, no free-form prose
scoring). RAGAS's Faithfulness (T-5.3) checks whether the ANSWER's claims
are supported by the retrieved CONTEXT as a whole; this metric checks a
narrower, citation-specific thing RAGAS does not: for each clause this
project's own Citation objects claim to cite, does that specific clause's
text actually support the specific claim attributed to it, and is any
clause the golden answer says is required left uncited?

Design, kept deliberately simple and auditable rather than clever:
  1. Programmatic component (no LLM, cannot drift): compare the set of
     clause_ids in GeneratedAnswer.citations against the golden item's
     expected_clause_ids. missing = expected - cited, extra = cited -
     expected. This alone catches the common failure modes (an omitted
     mandatory citation, a hallucinated clause_id) with zero judge cost
     or judge variance.
  2. LLM-as-judge component (G-Eval-style): for items with at least one
     citation, ask the judge model to read the answer text alongside the
     FULL TEXT of every cited clause (not just its id) and rate, per
     clause, whether that clause's text actually supports the portion of
     the answer attributed to it -- catching a citation that is present
     but wrong (cites the right-sounding clause for the wrong reason),
     which the programmatic set-comparison above cannot see. Structured
     JSON output (a 0/1 "supported" verdict per clause_id + one-sentence
     reason), not a single free-floating score, so a human can audit the
     judge's own reasoning against the corpus text -- this project's
     standing rule against unverified claims applies to the judge too.
  3. Per-item Citation Accuracy = (# cited clauses judged supported) /
     (# citations) if there are citations, else 1.0 if missing is also
     empty (nothing was owed and nothing was claimed) or 0.0 if something
     was owed and nothing was cited at all.

Same sandbox-network constraint as run_ragas_eval.py: needs a real
gpt-4o-mini call, run this yourself outside any sandbox.

Same `country` normalization as run_ragas_eval.py (see that file's
docstring for the full reasoning): free-text values like "UAE-DIFC" are
mapped to None via _normalize_country() rather than mis-filtering. The
DIFC-vs-mainland split is handled separately via a per-item
`jurisdiction_scope` field, set only for P-3a (unambiguous) and
deliberately left unset for P-3b/P-17 (their point is entity ambiguity --
forcing a jurisdiction there would defeat the probe).

Usage:
    .venv/bin/python eval/run_citation_accuracy_eval.py
    .venv/bin/python eval/run_citation_accuracy_eval.py --probe-id P-01

Requires OPENAI_API_KEY, an already-built build/vector_index/, and the
`openai` package (already in requirements.txt).
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
from grading.temporal_reasoner import ServiceFacts  # noqa: E402
from ingestion.embedder import EmbeddingCache, OpenAIEmbedder  # noqa: E402
from ingestion.index_units import build_indexable_units  # noqa: E402
from ingestion.logging_setup import get_logger  # noqa: E402
from ingestion.parser import parse_corpus  # noqa: E402
from retrieval.bm25_index import build_bm25_index  # noqa: E402
from retrieval.hybrid_search import HybridRetriever  # noqa: E402
from retrieval.vector_index import VectorIndex  # noqa: E402

_log = get_logger("eval.run_citation_accuracy_eval")

JUDGE_MODEL = "gpt-4o-mini"

JUDGE_SYSTEM_PROMPT = """You are auditing citations in an HR-policy answer for factual support.
You will be given the ANSWER TEXT and, for each clause it cites, that clause's FULL SOURCE TEXT.
For EACH cited clause, decide: does this clause's text actually support the part of the answer
that cites it? A clause "supports" the answer if the answer's claim attributed to that clause
(the figure, rule, or condition it states) is stated in, or a correct direct consequence of,
that clause's text -- not merely on the same general topic.
Return ONLY a JSON object of this exact shape, no prose outside it:
{"verdicts": [{"clause_id": "...", "supported": true|false, "reason": "one sentence"}]}
One verdict per cited clause, in the order given. Be strict: if the clause text does not contain
or directly entail the specific claim, mark supported=false and say what's missing."""


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
    return raw if raw in _VALID_COUNTRIES else None


def _judge_citations(client, answer_text: str, cited_pieces: list[tuple[str, str]]) -> list[dict]:
    """cited_pieces: list of (clause_id, source_text) for each Citation on
    the answer, in order. Returns the judge's per-clause verdict list."""
    if not cited_pieces:
        return []
    clause_block = "\n\n".join(
        f"--- Clause {cid} ---\n{text}" for cid, text in cited_pieces
    )
    user_prompt = f"ANSWER TEXT:\n{answer_text}\n\nCITED CLAUSES:\n{clause_block}"
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    try:
        parsed = json.loads(response.choices[0].message.content)
        return parsed.get("verdicts", [])
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        _log.warning("Judge response unparseable, treating as no supported citations: %s", exc)
        return [{"clause_id": cid, "supported": False, "reason": "judge response unparseable"} for cid, _ in cited_pieces]


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

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    index_path = REPO_ROOT / "build" / "vector_index"
    if not index_path.exists():
        print(f"{index_path} does not exist yet. Run scripts/build_vector_index.py --live first.", file=sys.stderr)
        return 1

    import openai
    client = openai.OpenAI()

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
        expected = set(item.get("expected_clause_ids") or [])
        row = {"probe_id": item["probe_id"], "status": result.status}

        if result.status != "ANSWERED":
            row["citation_accuracy"] = None
            row["note"] = "not ANSWERED -- citation accuracy undefined, see T-5.5 confusion matrix instead"
            per_item.append(row)
            continue

        cited_ids = [c.clause_id for c in result.answer.citations]
        cited_set = set(cited_ids)
        missing = sorted(expected - cited_set)
        extra = sorted(cited_set - expected)
        row["cited_clause_ids"] = cited_ids
        row["missing_expected_clause_ids"] = missing
        row["extra_clause_ids"] = extra

        piece_text_by_id = {p.clause_id: p.text for p in (result.pieces or [])}
        cited_pieces = [(cid, piece_text_by_id.get(cid, "(source text not found among retrieved pieces)"))
                        for cid in cited_ids]
        verdicts = _judge_citations(client, result.answer.text, cited_pieces)
        row["judge_verdicts"] = verdicts

        supported_count = sum(1 for v in verdicts if v.get("supported"))
        if not cited_ids:
            row["citation_accuracy"] = 1.0 if not expected else 0.0
        else:
            row["citation_accuracy"] = supported_count / len(cited_ids)
        per_item.append(row)

    scored = [r for r in per_item if r.get("citation_accuracy") is not None]
    mean_accuracy = sum(r["citation_accuracy"] for r in scored) / len(scored) if scored else None
    any_missing = sum(1 for r in scored if r.get("missing_expected_clause_ids"))
    any_extra = sum(1 for r in scored if r.get("extra_clause_ids"))

    print(f"\nScored {len(scored)}/{len(items)} items (rest were not ANSWERED).")
    print(f"Mean Citation Accuracy: {mean_accuracy:.3f}" if mean_accuracy is not None else "Mean Citation Accuracy: n/a")
    print(f"Items with a missing expected citation: {any_missing}/{len(scored)}")
    print(f"Items with an extra/unexpected citation: {any_extra}/{len(scored)}")

    out_path = REPO_ROOT / "build" / "citation_accuracy_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "judge_model": JUDGE_MODEL,
        "top_k": args.top_k,
        "reranked": reranker is not None,
        "scored_item_count": len(scored),
        "total_item_count": len(items),
        "mean_citation_accuracy": mean_accuracy,
        "items_missing_expected_citation": any_missing,
        "items_with_extra_citation": any_extra,
        "per_item": per_item,
    }, indent=2, default=str), encoding="utf-8")
    print(f"\nFull result written to {out_path}. Copy the summary numbers into "
          f"PROJECT_PLAN.md's Results ledger by hand -- this script does not edit the plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
