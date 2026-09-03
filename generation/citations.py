from __future__ import annotations

from generation.schema import Citation
from retrieval.hybrid_search import RetrievedPiece


def build_citation(piece: RetrievedPiece) -> Citation:
    doc = piece.unit.source_doc or piece.unit.source_act
    return Citation(
        clause_id=piece.clause_id,
        doc=doc,
        section=piece.unit.section,
        version=piece.unit.version,
        effective_date=piece.unit.effective_date,
    )


def build_citations(pieces: list[RetrievedPiece]) -> list[Citation]:
    citations: list[Citation] = []
    seen_clause_ids: set[str] = set()
    for p in pieces:
        if not p.unit.normative:
            continue
        if p.clause_id in seen_clause_ids:
            continue
        citations.append(build_citation(p))
        seen_clause_ids.add(p.clause_id)
    return citations