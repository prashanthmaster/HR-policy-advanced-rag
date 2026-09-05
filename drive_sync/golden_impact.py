"""
T-6.9 -- closes the loop between corpus freshness (T-6.4/T-6.5) and the
eval golden set.

Diagnosed in Session 10: T-6.5 already flags "this clause changed, a
human should review the corpus's own version metadata (effective_date,
supersedes/superseded_by)." That flag says nothing about the eval's own
ground truth -- if a golden probe's recorded `golden_answer` quotes a
number from that same clause, the golden answer can silently go stale
the moment the clause changes, and nothing catches it until (or unless)
someone happens to re-run an answer-text eval like RAGAS Answer
Correctness or Citation Accuracy against the now-outdated answer key.

This module is the missing cross-reference. It is deliberately as small
and dumb as the problem allows: every golden probe already records which
clauses its `golden_answer` depends on (`expected_clause_ids`), and every
re-index already knows which clause_ids just changed (T-6.5's
VersionEvent.clause_id). Intersecting those two sets is the whole fix --
no NLP, no guessing which sentence in the golden_answer is now wrong,
just "these two things both mention this clause_id, so a human should
look." Same "flag, don't fix" discipline as T-6.5 itself: this never
edits the golden set, it only tells a human which probes to check.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_GOLDEN_SET_PATH = Path(__file__).resolve().parent.parent / "eval" / "golden" / "scored_golden_set.json"


@dataclass(frozen=True)
class AffectedProbe:
    probe_id: str
    query: str
    matched_clause_ids: tuple[str, ...]


def load_golden_items(path: Path = _GOLDEN_SET_PATH) -> list[dict]:
    """Loads the golden set's `items` list. Kept as a thin, separate
    function (rather than inlining json.loads at the call site) so tests
    can point it at a small fixture file instead of the real 24-item set."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["items"]


def find_affected_probes(changed_clause_ids: set[str], golden_items: list[dict]) -> list[AffectedProbe]:
    """For each golden probe whose `expected_clause_ids` intersects
    changed_clause_ids, returns an AffectedProbe naming which of its
    clauses changed. Golden items with no `expected_clause_ids` (e.g. a
    MUST_REFUSE probe with no valid clause to cite) are skipped -- there
    is nothing to cross-check for those. Pure function, no I/O, no API
    calls -- safe to call on every re-index run."""
    affected: list[AffectedProbe] = []
    for item in golden_items:
        expected = set(item.get("expected_clause_ids") or [])
        matched = expected & changed_clause_ids
        if matched:
            affected.append(
                AffectedProbe(
                    probe_id=item["probe_id"],
                    query=item["query"],
                    matched_clause_ids=tuple(sorted(matched)),
                )
            )
    return affected
