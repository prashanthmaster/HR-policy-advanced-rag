from __future__ import annotations

from langsmith import traceable

from generation.citations import build_citations
from generation.formula import (
    FORMULAS,
    compute_flat_gratuity,
    compute_leave_segment,
    compute_tenure_banded_days,
)
from generation.schema import GeneratedAnswer
from generation.supersession import check_supersession
from grading.temporal_reasoner import TemporalWorking
from retrieval.hybrid_search import RetrievedPiece


def _compute_from_workings(workings: list[TemporalWorking], pieces_clause_ids: set[str]) -> tuple[list[str], float | None, float | None]:
    """Phase 5 addition: turn TemporalWorking's structural output into a
    number, where generation/formula.py has a matching formula AND the
    needed ServiceFacts were actually supplied. Returns extra narrative
    lines plus (computed_amount, computed_days) -- either or both may
    stay None, which is the correct behaviour when a formula or a fact
    is missing (report the method, never invent a figure).

    Deliberately handles two distinct shapes, matching the two real
    formula kinds in generation/formula.FORMULAS:
      - a single POINT_IN_TIME/self-contained working whose
        governing_piece has a formula (India gratuity, UAE's
        tenure-banded gratuity day-count);
      - a SEGMENTED_ACCRUAL working with >1 segment, each segment's
        governing_piece looked up separately and summed (India leave
        18->24 days).
    """
    lines: list[str] = []
    amount: float | None = None
    days: float | None = None

    for w in workings:
        if w.governing_piece is not None and w.service_start_date and w.valuation_date:
            formula = FORMULAS.get(w.governing_piece.clause_id)
            if formula is None:
                continue
            if formula.kind == "flat_days_per_year":
                comp = compute_flat_gratuity(
                    formula, w.service_start_date, w.valuation_date, w.monthly_wage, pieces_clause_ids,
                )
                if comp.amount is not None:
                    amount = (amount or 0.0) + comp.amount
                    if comp.ceiling_applied:
                        lines.append(
                            f"Computed: uncapped {comp.uncapped_amount:,.2f}, capped to {comp.amount:,.2f} "
                            f"by {comp.ceiling_applied}."
                        )
                    else:
                        lines.append(f"Computed amount: {comp.amount:,.2f}.")
                elif comp.note:
                    lines.append(comp.note)
            elif formula.kind == "tenure_banded_days_per_year":
                comp = compute_tenure_banded_days(formula, w.service_start_date, w.valuation_date)
                if comp.total_days is not None:
                    days = (days or 0.0) + comp.total_days
                    lines.append(f"Computed: {comp.total_days:g} days total. {comp.note}")

        if w.segments:
            segment_total = 0.0
            all_have_formula = True
            for seg in w.segments:
                formula = FORMULAS.get(seg.governing_piece.clause_id)
                if formula is None or formula.kind != "flat_days_per_year_proportional" or seg.start is None or seg.end is None:
                    all_have_formula = False
                    break
                segment_total += compute_leave_segment(formula, seg.start, seg.end)
            if all_have_formula and w.segments:
                days = (days or 0.0) + segment_total
                lines.append(f"Computed: {segment_total:g} days total across {len(w.segments)} segment(s).")

    return lines, amount, days


def _pieces_actually_used(pieces: list[RetrievedPiece], workings: list[TemporalWorking]) -> list[RetrievedPiece]:
    """Bug fix, 2026-09-04 (Session 5): citations/supersession-checking used
    to run over the FULL retrieved-and-graded `pieces` list unconditionally,
    which is right when there's no temporal reasoning (every normative piece
    really is narrated verbatim, see the `if not workings` branch below) but
    wrong once `workings` exist -- the narrative only ever discusses each
    working's `governing_piece` / `segments[*].governing_piece` /
    `alternatives` (see grading/temporal_reasoner.py), never the other
    5-9 pieces retrieval also returned as candidates. Citing the whole
    retrieved set regardless produced a real defect: a live T-5.4 run
    showed 7/7 ANSWERED items over-citing (mean Citation Accuracy 0.106).
    This narrows citations/supersession-notes down to what the narrative
    actually relied on -- retrieval keeps its full breadth (still needed
    for CRAG sufficiency grading and corrective re-query), only what gets
    STAMPED as a source changes."""
    if not workings:
        return [p for p in pieces if p.unit.normative]
    used: list[RetrievedPiece] = []
    seen_ids: set[str] = set()
    for w in workings:
        candidates = list(w.alternatives)
        if w.governing_piece is not None:
            candidates.append(w.governing_piece)
        candidates.extend(seg.governing_piece for seg in w.segments)
        for c in candidates:
            if c.clause_id not in seen_ids:
                used.append(c)
                seen_ids.add(c.clause_id)
    return used


class TemplateGenerator:
    """Deterministic, no LLM. Assembles an answer purely by stitching
    together clause text, T-4.3's narrative lines, and (Phase 5) a small
    deterministic arithmetic layer (generation/formula.py) -- nothing
    here is invented, so nothing here can hallucinate."""

    @traceable(name="generate_answer", run_type="chain")
    def generate(
        self,
        query: str,
        pieces: list[RetrievedPiece],
        workings: list[TemporalWorking],
    ) -> GeneratedAnswer:
        lines: list[str] = []
        missing: list[str] = []

        if not workings:
            for p in pieces:
                if p.unit.normative:
                    lines.append(p.text)
        else:
            for w in workings:
                lines.extend(w.narrative)
                missing.extend(w.missing_facts)

        used_pieces = _pieces_actually_used(pieces, workings)
        citations = build_citations(used_pieces)

        computed_amount: float | None = None
        computed_days: float | None = None
        if not missing and workings:
            pieces_clause_ids = {p.clause_id for p in pieces}
            compute_lines, computed_amount, computed_days = _compute_from_workings(workings, pieces_clause_ids)
            lines.extend(compute_lines)

        if missing:
            lines.append(f"Cannot give a final answer: missing {', '.join(missing)}.")

        notes, warning = check_supersession(used_pieces)
        lines.extend(notes)
        if warning:
            lines.append(warning)

        return GeneratedAnswer(
            text="\n".join(lines),
            citations=citations,
            used_temporal_reasoning=bool(workings),
            computed_amount=computed_amount,
            computed_days=computed_days,
            superseded_warning=warning,
        )
