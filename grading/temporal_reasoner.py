"""
T-4.3: apply the four temporal_applicability classes over a graded,
possibly-corrected set of RetrievedPieces, and show the working.

This module does the STRUCTURAL reasoning -- which version(s) govern
which sub-period, whether a cohort test is met, which alternatives are
in play -- not the final arithmetic (a leave-day count, a rupee amount).
That split matches the rest of Phase 4: generation (T-4.4) turns a
TemporalWorking into prose with numbers, from context only; this module
decides the SHAPE of the computation the four architecture-findings
classes require, deterministically, so it's fully unit-testable against
the real corpus without an LLM call.

Ground truth for every branch below is Finding 1
(slot4_architecture_findings.md) plus what T-4.1/T-4.2 already
established while building the grader: SEGMENTED_ACCRUAL/GRANDFATHERED
is a per-CLAUSE property, not a per-LINEAGE one -- some lineages tagged
SEGMENTED_ACCRUAL are actually self-contained single clauses (DIFC
annual leave, "accruing proportionately", no supersedes/superseded_by),
and only an amendment PAIR (supersedes/superseded_by set) needs the
split-and-sum shown here.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from ingestion.logging_setup import get_logger
from ingestion.schema import TemporalApplicability
from retrieval.hybrid_search import RetrievedPiece

_log = get_logger("grading.temporal_reasoner")

_COHORT_RULE_RE = re.compile(r"service_commenced_before\((\d{4}-\d{2}-\d{2})\)")


@dataclass
class ServiceFacts:
    """The employee-specific facts a temporal computation needs. None of
    these come from the corpus -- they come from the query (parsed by
    generation/an upstream fact-extraction step, out of this module's
    scope) or from a clarification round-trip (T-4.5) when the query
    doesn't supply them."""

    service_start_date: dt.date | None = None
    valuation_date: dt.date | None = None
    """The trigger/termination/'as of' date the computation is anchored
    to -- what Finding 1 calls the trigger-event date for POINT_IN_TIME,
    and the end of the period being segmented for SEGMENTED_ACCRUAL."""


@dataclass
class Segment:
    start: dt.date | None
    end: dt.date | None
    governing_piece: RetrievedPiece


@dataclass
class TemporalWorking:
    applicability: TemporalApplicability
    narrative: list[str] = field(default_factory=list)
    """Human-readable working, one step per line -- this is what a
    generation prompt quotes verbatim to "show the working" rather than
    silently asserting a conclusion."""
    governing_piece: RetrievedPiece | None = None
    """Set for POINT_IN_TIME (and GRANDFATHERED once the cohort test is
    resolved) -- the single clause that governs the whole computation."""
    segments: list[Segment] = field(default_factory=list)
    """Set for SEGMENTED_ACCRUAL -- one entry per sub-period, in order."""
    alternatives: list[RetrievedPiece] = field(default_factory=list)
    """Set for ELECTIVE -- every candidate the employee may elect between."""
    missing_facts: list[str] = field(default_factory=list)
    """Facts this reasoning needed but ServiceFacts didn't supply --
    T-4.5's clarification contract is the consumer of this list, not an
    error condition raised here."""


def _lineage_pair(pieces: list[RetrievedPiece]) -> tuple[RetrievedPiece, RetrievedPiece]:
    """The two amendment-pair pieces, older-first, identified by
    supersedes/superseded_by (see module docstring) rather than by
    effective_date alone -- a lineage could in principle carry unrelated
    clauses sharing an id by coincidence; the explicit link is the
    contract, not just chronology."""
    by_id = {p.clause_id: p for p in pieces}
    newer = next((p for p in pieces if p.unit.supersedes and p.unit.supersedes in by_id), None)
    if newer is None:
        raise ValueError("no amendment pair found among the given pieces (need supersedes/superseded_by)")
    older = by_id[newer.unit.supersedes]
    return older, newer


def reason_point_in_time(piece: RetrievedPiece, facts: ServiceFacts) -> TemporalWorking:
    """Finding 1's marquee trap: the intuitive move on a straddling
    service period is to split it. POINT_IN_TIME is exactly the class
    where that intuition is wrong -- the version in force on the
    TRIGGER date (valuation_date: termination, payout, the date being
    asked "as of") governs the WHOLE period, service start date is
    irrelevant to which version applies. P-01 (India gratuity ceiling)
    is this class."""
    narrative = [
        f"{piece.clause_id} is POINT_IN_TIME: the version in force on the trigger date "
        "governs the entire computation. Service does not get split at a version boundary "
        "for this class, however long the service period is or however many amendments it spans.",
    ]
    if piece.unit.effective_date is not None:
        narrative.append(
            f"Governing version effective from {piece.unit.effective_date.isoformat()}."
        )
    if facts.valuation_date is not None and piece.unit.effective_date is not None:
        if piece.unit.effective_date <= facts.valuation_date:
            narrative.append(
                f"Trigger date {facts.valuation_date.isoformat()} is on or after that effective date, "
                "so this version governs the whole computation -- not split by service start date."
            )
        else:
            narrative.append(
                f"WARNING: trigger date {facts.valuation_date.isoformat()} precedes this version's "
                "effective date -- this piece should not have been selected as governing for that date."
            )
    return TemporalWorking(
        applicability=TemporalApplicability.POINT_IN_TIME,
        narrative=narrative,
        governing_piece=piece,
    )


def reason_segmented_accrual(pieces: list[RetrievedPiece], facts: ServiceFacts) -> TemporalWorking:
    """P-02 (India leave 18->24) and P-3a (DIFC gratuity->DEWS) shape:
    split service at the amendment boundary, compute each segment under
    its own version, sum. Requires both amendment-pair pieces already
    present (T-4.1/T-4.2's job) and both service_start_date and
    valuation_date to actually place the boundary inside the period --
    without those two facts this returns the segment structure it CAN
    determine (which version governs which side of the boundary) but
    flags the dates it's missing rather than guessing a period."""
    older, newer = _lineage_pair(pieces)
    boundary = newer.unit.effective_date
    narrative = [
        f"{older.clause_id} (effective {older.unit.effective_date}) was superseded by "
        f"{newer.clause_id} (effective {boundary}) -- SEGMENTED_ACCRUAL: split service at "
        f"{boundary}, compute each segment under its own version, and sum. Do not apply "
        "either version to the whole period.",
    ]
    missing_facts = []
    if facts.service_start_date is None:
        missing_facts.append("service_start_date")
    if facts.valuation_date is None:
        missing_facts.append("valuation_date")

    segments: list[Segment] = []
    if not missing_facts and boundary is not None:
        if facts.service_start_date >= boundary:
            # whole period is post-boundary; only the newer version applies,
            # but this is still reported as a (degenerate) single segment
            # rather than silently switching to POINT_IN_TIME reasoning.
            segments = [Segment(start=facts.service_start_date, end=facts.valuation_date, governing_piece=newer)]
            narrative.append(
                f"Service start {facts.service_start_date} is on or after the boundary -- "
                f"the entire period falls under {newer.clause_id}, one segment, no split needed."
            )
        elif facts.valuation_date <= boundary:
            segments = [Segment(start=facts.service_start_date, end=facts.valuation_date, governing_piece=older)]
            narrative.append(
                f"Valuation date {facts.valuation_date} is on or before the boundary -- "
                f"the entire period falls under {older.clause_id}, one segment, no split needed."
            )
        else:
            segments = [
                Segment(start=facts.service_start_date, end=boundary, governing_piece=older),
                Segment(start=boundary, end=facts.valuation_date, governing_piece=newer),
            ]
            narrative.append(
                f"Service genuinely straddles the boundary: segment 1 is {facts.service_start_date} to "
                f"{boundary} under {older.clause_id}; segment 2 is {boundary} to {facts.valuation_date} "
                f"under {newer.clause_id}. Sum the two segments' computed entitlements."
            )
    else:
        narrative.append(
            "Cannot place the boundary within the service period without service_start_date and "
            "valuation_date -- reporting the two candidate segment-governing clauses without dates."
        )

    return TemporalWorking(
        applicability=TemporalApplicability.SEGMENTED_ACCRUAL,
        narrative=narrative,
        segments=segments,
        missing_facts=missing_facts,
    )


def reason_grandfathered(piece: RetrievedPiece, facts: ServiceFacts) -> TemporalWorking:
    """P-06 shape: the cohort test (IndexableUnit.cohort_rule) decides
    which population this clause applies to. Both the pre- and
    post-amendment versions can be simultaneously "current" for
    different cohorts -- this is population-scoped, not time-segmented,
    so there is no split-and-sum, only a yes/no test against
    service_start_date. Missing service_start_date is exactly what makes
    P-06 MUST_CLARIFY rather than MUST_ANSWER (Finding 5) -- that
    contract is T-4.5's job; this function only surfaces the missing
    fact."""
    if not piece.unit.cohort_rule:
        return TemporalWorking(
            applicability=TemporalApplicability.GRANDFATHERED,
            narrative=[f"{piece.clause_id} is GRANDFATHERED but carries no cohort_rule -- cannot apply."],
            missing_facts=["cohort_rule"],
        )

    match = _COHORT_RULE_RE.match(piece.unit.cohort_rule.strip())
    if not match:
        return TemporalWorking(
            applicability=TemporalApplicability.GRANDFATHERED,
            narrative=[f"{piece.clause_id}: cohort_rule '{piece.unit.cohort_rule}' is not a recognised pattern."],
            missing_facts=["cohort_rule"],
        )
    boundary = dt.date.fromisoformat(match.group(1))

    narrative = [
        f"{piece.clause_id} is GRANDFATHERED: applies only to employees whose service commenced "
        f"before {boundary.isoformat()} (cohort_rule: {piece.unit.cohort_rule}). This is a population "
        "test, not a period split -- an employee either is or isn't in the grandfathered cohort.",
    ]
    if facts.service_start_date is None:
        narrative.append("Employee's service_start_date is not supplied -- cannot resolve the cohort test.")
        return TemporalWorking(
            applicability=TemporalApplicability.GRANDFATHERED,
            narrative=narrative,
            missing_facts=["service_start_date"],
        )

    applies = facts.service_start_date < boundary
    narrative.append(
        f"Service start {facts.service_start_date.isoformat()} is "
        f"{'before' if applies else 'on or after'} {boundary.isoformat()} -- clause "
        f"{'applies' if applies else 'does not apply'} to this employee."
    )
    return TemporalWorking(
        applicability=TemporalApplicability.GRANDFATHERED,
        narrative=narrative,
        governing_piece=piece if applies else None,
    )


def reason_elective(pieces: list[RetrievedPiece], facts: ServiceFacts) -> TemporalWorking:
    """No real corpus fixture yet (see grading/crag_grader.py's same
    caveat) -- generic handling: present every alternative; which one is
    more favourable is an arithmetic comparison generation (T-4.4) makes
    from the actual computed figures, not something this structural
    layer decides."""
    narrative = [
        "ELECTIVE: the employee may elect whichever of the following produces the more "
        f"favourable outcome: {', '.join(p.clause_id for p in pieces)}. Both must be computed "
        "and compared -- do not pick one without computing both.",
    ]
    return TemporalWorking(
        applicability=TemporalApplicability.ELECTIVE,
        narrative=narrative,
        alternatives=list(pieces),
    )


def reason_over_pieces(pieces: list[RetrievedPiece], facts: ServiceFacts) -> list[TemporalWorking]:
    """Entry point: group the (already graded-sufficient) normative
    pieces by lineage and dispatch each group to its class's reasoner.
    Pieces with no temporal_applicability (untracked / no version
    history) are not reasoned over here -- nothing to show working on."""
    by_lineage: dict[str, list[RetrievedPiece]] = {}
    singles: list[RetrievedPiece] = []
    for p in pieces:
        if not p.unit.normative or p.unit.temporal_applicability is None:
            continue
        if p.unit.lineage_id:
            by_lineage.setdefault(p.unit.lineage_id, []).append(p)
        else:
            singles.append(p)

    workings: list[TemporalWorking] = []
    seen_clause_ids: set[str] = set()

    for lineage_id, group in by_lineage.items():
        applicability = group[0].unit.temporal_applicability
        if any(p.unit.temporal_applicability != applicability for p in group):
            _log.warning("lineage %s has mixed temporal_applicability across retrieved pieces", lineage_id)

        is_amendment_pair = any(p.unit.supersedes or p.unit.superseded_by for p in group)

        if applicability == TemporalApplicability.POINT_IN_TIME.value:
            for p in group:
                workings.append(reason_point_in_time(p, facts))
                seen_clause_ids.add(p.clause_id)
        elif applicability == TemporalApplicability.SEGMENTED_ACCRUAL.value and is_amendment_pair and len(group) >= 2:
            workings.append(reason_segmented_accrual(group, facts))
            seen_clause_ids.update(p.clause_id for p in group)
        elif applicability == TemporalApplicability.GRANDFATHERED.value:
            for p in group:
                workings.append(reason_grandfathered(p, facts))
                seen_clause_ids.add(p.clause_id)
        elif applicability == TemporalApplicability.ELECTIVE.value and len(group) >= 2:
            workings.append(reason_elective(group, facts))
            seen_clause_ids.update(p.clause_id for p in group)
        else:
            # SEGMENTED_ACCRUAL/ELECTIVE without an amendment pair/pair of
            # alternatives (e.g. DIFC-LEAVE): self-contained, no split.
            for p in group:
                workings.append(
                    TemporalWorking(
                        applicability=TemporalApplicability(applicability),
                        narrative=[
                            f"{p.clause_id} is tagged {applicability} but carries no amendment pair or "
                            "alternative in the retrieved set -- treated as self-contained (its own text "
                            "already states how the rate accrues)."
                        ],
                        governing_piece=p,
                    )
                )
                seen_clause_ids.add(p.clause_id)

    for p in singles:
        if p.clause_id in seen_clause_ids:
            continue
        applicability = p.unit.temporal_applicability
        if applicability == TemporalApplicability.POINT_IN_TIME.value:
            workings.append(reason_point_in_time(p, facts))
        elif applicability == TemporalApplicability.GRANDFATHERED.value:
            workings.append(reason_grandfathered(p, facts))
        else:
            workings.append(
                TemporalWorking(
                    applicability=TemporalApplicability(applicability),
                    narrative=[f"{p.clause_id} ({applicability}) has no lineage_id -- treated as self-contained."],
                    governing_piece=p,
                )
            )

    return workings
