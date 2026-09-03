"""
T-4.6: supersession flagging in answers (FM-E6).

Two distinct things, not to be conflated:

  1. An AMENDMENT NOTE -- informational, no warning. When a cited clause
     has `supersedes` set, it IS the current version and there's nothing
     wrong with citing it; the note just tells the reader the rule has a
     history ("X supersedes Y, effective <date>"). This fires for the
     legitimate SEGMENTED_ACCRUAL case too (both DIFC-L2-2019-DEWS and
     DIFC-EOSB-LEGACY-GRATUITY cited together, correctly, per T-4.3) --
     that's not a bug, it's exactly what should be visible to the reader.

  2. A STALE-CITATION WARNING -- a genuine safety net. When a cited
     clause has `superseded_by` set and that replacement clause is NOT
     also among the citations, the answer is citing a clause that is no
     longer current with nothing to show it was superseded in context.
     Under the normal retrieve() -> grade -> generate path this should
     never happen (select_current_as_of already excludes superseded
     versions unless deliberately queried as-of a past date, and T-4.2's
     correction only ADDS the sibling back in for the legitimate split
     case) -- so if it fires, it's worth surfacing loudly rather than
     assuming the pipeline upstream got it right.
"""

from __future__ import annotations

from retrieval.hybrid_search import RetrievedPiece


def check_supersession(pieces: list[RetrievedPiece]) -> tuple[list[str], str | None]:
    normative = [p for p in pieces if p.unit.normative]
    cited_clause_ids = {p.clause_id for p in normative}

    notes: list[str] = []
    warnings: list[str] = []

    for p in normative:
        if p.unit.supersedes:
            date_part = f", effective {p.unit.effective_date.isoformat()}" if p.unit.effective_date else ""
            notes.append(f"Note: {p.clause_id} supersedes {p.unit.supersedes}{date_part}.")

        if p.unit.superseded_by and p.unit.superseded_by not in cited_clause_ids:
            warnings.append(
                f"WARNING: {p.clause_id} has been superseded by {p.unit.superseded_by}, "
                "which is not part of this answer -- this citation may be stale."
            )

    warning = " ".join(warnings) if warnings else None
    return notes, warning
