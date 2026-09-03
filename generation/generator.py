from __future__ import annotations

from langsmith import traceable

from generation.citations import build_citations
from generation.schema import GeneratedAnswer
from generation.supersession import check_supersession
from grading.temporal_reasoner import TemporalWorking
from retrieval.hybrid_search import RetrievedPiece


class TemplateGenerator:
    """Deterministic, no LLM. Assembles an answer purely by stitching
    together clause text and T-4.3's narrative lines -- nothing here is
    invented, so nothing here can hallucinate."""

    @traceable(name="generate_answer", run_type="chain")
    def generate(
        self,
        query: str,
        pieces: list[RetrievedPiece],
        workings: list[TemporalWorking],
    ) -> GeneratedAnswer:
        citations = build_citations(pieces)
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

        if missing:
            lines.append(f"Cannot give a final answer: missing {', '.join(missing)}.")

        notes, warning = check_supersession(pieces)
        lines.extend(notes)
        if warning:
            lines.append(warning)

        return GeneratedAnswer(
            text="\n".join(lines),
            citations=citations,
            used_temporal_reasoning=bool(workings),
            superseded_warning=warning,
        )