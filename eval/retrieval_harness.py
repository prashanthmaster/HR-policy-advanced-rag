"""
T-3.6: retrieval-only harness -- Context Precision + Context Recall over
the adversarial probe set, measured BEFORE any generation code exists
(PROJECT_PLAN.md's stated reason: a generation bug and a retrieval bug
produce the same symptom, a wrong answer, so retrieval must be
attributable on its own first -- and it's the honest answer to "how do
you know the reranker earns its place?").

Ground truth source: eval/probe_fixture_map.json's "probes" mapping
(probe_id -> list of clause_ids required to answer it), built during
corpus construction (T-1.x) specifically so this kind of check is
possible. Probe query TEXT is parsed straight out of
eval/golden/adversarial_probe_set.md rather than hand-copied, so the two
files can't silently drift apart.

Metric definitions (retrieval-only, deliberately simpler than the full
RAGAS LLM-judged versions Phase 5 uses over generated answers -- there is
no generated answer yet, only a retrieved set, so a plain set-overlap
metric against the known-correct source clause_ids is the honest
retrieval-only analogue, not a stand-in for RAGAS's Context Precision/
Recall):
  - context_precision@k = |retrieved_clause_ids ∩ expected| / |retrieved_clause_ids|
  - context_recall@k    = |retrieved_clause_ids ∩ expected| / |expected|
  clause_ids are compared, not piece_ids, since a probe's expected set is
  written at clause granularity and a clause can produce >1 retrieval
  piece (T-2.4's table rows).

Scope note -- which probes are scored: a probe with an EMPTY expected-
clause list in probe_fixture_map.json is not a retrieval-precision/recall
item (P-21/P-26/P-29/P-41 are MUST_CLARIFY/MUST_REFUSE probes with no
single correct source; scoring them here would be meaningless, not
measuring something zero). P-39 (DELIBERATE_ABSENCE) is also excluded --
its correct retrieval outcome is "nothing", which this precision/recall
formulation isn't shaped to score either; it belongs in Phase 5's
confusion-matrix / over-refusal counter instead (Finding 3), not here.
Excluded probe ids are recorded in the result, not silently dropped.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ingestion.logging_setup import get_logger
from retrieval.hybrid_search import HybridRetriever
from retrieval.hybrid_search import DEFAULT_MIN_RERANK_SCORE
from retrieval.reranker import Reranker

_log = get_logger("eval.retrieval_harness")

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE_SET_MD = REPO_ROOT / "eval" / "golden" / "adversarial_probe_set.md"
PROBE_FIXTURE_MAP = REPO_ROOT / "eval" / "probe_fixture_map.json"

_NARRATIVE_RE = re.compile(r'\*\*(P-\d+[a-z]?)\b[^\n*]*\*\*\s*\n\s*\n>\s*"([^"]+)"')
_TABLE_RE = re.compile(r'^\|\s*(P-\d+[a-z]?)\s*\|[^|]*\|\s*"([^"]+)"', flags=re.MULTILINE)

DELIBERATE_ABSENCE = "DELIBERATE_ABSENCE"


def load_probe_queries(path: Path = PROBE_SET_MD) -> dict[str, str]:
    """probe_id -> query text, parsed from the probe set markdown. Every
    probe appears either in narrative form (P-01..P-03, P-3a, P-3b) or as
    a table row (everything else) -- both patterns are tried; the first
    match wins, so a probe present in both never gets overwritten by a
    second, differently-worded occurrence."""
    text = path.read_text(encoding="utf-8")
    probes: dict[str, str] = {}
    for m in _NARRATIVE_RE.finditer(text):
        probes[m.group(1)] = m.group(2)
    for m in _TABLE_RE.finditer(text):
        probes.setdefault(m.group(1), m.group(2))
    return probes


def load_expected_clauses(path: Path = PROBE_FIXTURE_MAP) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["probes"]


@dataclass
class ProbeRetrievalResult:
    probe_id: str
    query: str
    expected: list[str]
    retrieved_clause_ids: list[str]
    precision: float
    recall: float


@dataclass
class RetrievalHarnessReport:
    per_probe: list[ProbeRetrievalResult]
    excluded_probe_ids: list[str]
    mean_precision: float
    mean_recall: float
    scored_probe_count: int


def _score_one(expected: set[str], retrieved: list[str]) -> tuple[float, float]:
    retrieved_set = set(retrieved)
    hit = expected & retrieved_set
    precision = len(hit) / len(retrieved_set) if retrieved_set else 0.0
    recall = len(hit) / len(expected) if expected else 0.0
    return precision, recall


def run_retrieval_harness(
    retriever: HybridRetriever,
    top_k: int = 10,
    as_of_date: dt.date | None = None,
    reranker: Reranker | None = None,
    probe_queries: dict[str, str] | None = None,
    expected_by_probe: dict[str, list[str]] | None = None,
    min_rerank_score: float | None = DEFAULT_MIN_RERANK_SCORE,
) -> RetrievalHarnessReport:
    """min_rerank_score defaults to the Session 6 calibrated floor (Phase 3
    reopened bug fix) -- the T-3.6 re-run should use this default so the
    Results Ledger's "after" numbers reflect production behaviour. Pass
    None explicitly to reproduce the original 3 Sep pre-fix numbers for
    comparison."""
    probe_queries = probe_queries if probe_queries is not None else load_probe_queries()
    expected_by_probe = expected_by_probe if expected_by_probe is not None else load_expected_clauses()

    per_probe: list[ProbeRetrievalResult] = []
    excluded: list[str] = []

    for probe_id, query in probe_queries.items():
        expected_list = expected_by_probe.get(probe_id, [])
        if not expected_list or expected_list == [DELIBERATE_ABSENCE]:
            excluded.append(probe_id)
            continue

        results = retriever.retrieve(query, top_k=top_k, as_of_date=as_of_date, reranker=reranker, min_rerank_score=min_rerank_score)
        retrieved_clause_ids = [r.clause_id for r in results]
        expected_set = set(expected_list)
        precision, recall = _score_one(expected_set, retrieved_clause_ids)

        per_probe.append(
            ProbeRetrievalResult(
                probe_id=probe_id,
                query=query,
                expected=expected_list,
                retrieved_clause_ids=retrieved_clause_ids,
                precision=precision,
                recall=recall,
            )
        )

    mean_precision = sum(r.precision for r in per_probe) / len(per_probe) if per_probe else 0.0
    mean_recall = sum(r.recall for r in per_probe) / len(per_probe) if per_probe else 0.0

    _log.info(
        "retrieval harness: scored %d probes (excluded %d), mean precision=%.3f mean recall=%.3f",
        len(per_probe), len(excluded), mean_precision, mean_recall,
    )

    return RetrievalHarnessReport(
        per_probe=per_probe,
        excluded_probe_ids=sorted(excluded),
        mean_precision=mean_precision,
        mean_recall=mean_recall,
        scored_probe_count=len(per_probe),
    )
