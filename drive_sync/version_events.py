"""
T-6.5 -- clause-level version-event detection (Option B, confirmed by
Prashanth 4 Sep 2026: detect and flag, never auto-decide).

Wires ingestion/change_kind.py's classify_change() (built and unit-tested
in Phase 2, T-2.5, but never actually called by anything until now) in at
clause granularity: for a changed document, compares every clause_id's old
body against its new body and classifies what kind of change it was.

Deliberately does NOT auto-generate a new versioned clause_id, guess an
effective date out of the prose, or write supersedes/superseded_by fields
itself. This project's standing rule is never to invent an unverified fact
-- pattern-matching a date or a "this supersedes that" relationship out of
free text is exactly that kind of guess, and every other versioned clause
pair already in this corpus was authored with real lineage fields, never
inferred. So a SUBSTANTIVE or SUNSET classification here means "a human
needs to confirm and fill in the version metadata (effective_date, a new
clause_id, supersedes/superseded_by)" -- it is a flag, not an action. The
change is still fully re-indexed by T-6.4 regardless (retrieval must
always reflect what's actually live in the source document); this module
only decides what to tell a human, never what to write to the corpus.

This is the same "flag, don't fix" discipline already used elsewhere in
this project (e.g. the P-01/P-17 reranker-ordering limitation, Convention
15) applied to a new kind of finding.
"""

from __future__ import annotations

from dataclasses import dataclass

from ingestion.change_kind import ChangeKind, classify_change
from ingestion.schema import Chunk


@dataclass(frozen=True)
class VersionEvent:
    clause_id: str
    kind: ChangeKind
    old_body: str | None
    new_body: str | None
    needs_human_review: bool
    note: str


# Kinds that mean "the retrievable text changed in a way that could affect
# what an answer says" -- these are the ones a human should look at before
# the corpus's own version metadata (effective_date, supersedes/
# superseded_by, lineage_id) is trusted to still be accurate.
_REVIEW_KINDS = {ChangeKind.SUBSTANTIVE, ChangeKind.SUNSET, ChangeKind.ADDITION}

_NOTES = {
    ChangeKind.SUBSTANTIVE: (
        "Clause body changed in a legally meaningful way (not just whitespace/"
        "punctuation). If this represents a real policy change effective on a "
        "specific date, a human needs to confirm that and update this clause's "
        "own version metadata -- a new versioned clause_id with its own "
        "effective_date, supersedes pointing back at the prior version, and "
        "the prior version's superseded_by set. Nothing was written "
        "automatically; the live index now reflects the new text either way."
    ),
    ChangeKind.SUNSET: (
        "This clause no longer appears in the document. If it was genuinely "
        "withdrawn/repealed, a human should confirm that and mark it "
        "superseded/historical rather than silently dropping it from the "
        "record -- it has already been removed from the live index, but its "
        "version history needs a human decision, not a guess."
    ),
    ChangeKind.ADDITION: (
        "A clause_id that wasn't previously in this document. If this is "
        "meant to be a new version of an existing rule, it should carry "
        "supersedes pointing at the prior clause_id and a real effective_date "
        "-- check whether that's actually been done, or whether it's simply "
        "unrelated new content."
    ),
}


def detect_version_events(old_chunks: list[Chunk], new_chunks: list[Chunk]) -> list[VersionEvent]:
    """Compare a document's clauses before and after an edit, one clause_id
    at a time. Returns one VersionEvent per clause_id that isn't a pure
    NO_OP/EDITORIAL change -- callers should surface these to a human
    (T-6.7's demo, or a real ops workflow) rather than act on them."""
    old_by_id = {c.metadata.clause_id: c.body for c in old_chunks}
    new_by_id = {c.metadata.clause_id: c.body for c in new_chunks}

    all_ids = sorted(set(old_by_id) | set(new_by_id))
    events: list[VersionEvent] = []

    for clause_id in all_ids:
        old_body = old_by_id.get(clause_id)
        new_body = new_by_id.get(clause_id)
        kind = classify_change(old_body, new_body)

        if kind in (ChangeKind.NO_OP, ChangeKind.EDITORIAL):
            continue

        events.append(
            VersionEvent(
                clause_id=clause_id,
                kind=kind,
                old_body=old_body,
                new_body=new_body,
                needs_human_review=kind in _REVIEW_KINDS,
                note=_NOTES.get(kind, ""),
            )
        )

    return events
