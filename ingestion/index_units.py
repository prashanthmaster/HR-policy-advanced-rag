"""
Unifies the two chunking paths -- ingestion.chunker (prose) and
ingestion.table_serializer (tables) -- into one common shape that both
T-2.6 (BM25) and T-2.7 (vector) index builders consume identically. This
is deliberately its own module rather than logic duplicated in each index
builder: "what gets indexed, and with what metadata attached" should be
decided once, not twice, or the two indexes could silently drift apart on
which clauses they cover.

Every IndexableUnit carries the retrieval-time filtering fields straight
from the clause's metadata (country, effective_date, temporal_applicability,
normative, jurisdiction_scope) because Phase 3's retrieval filtering
(effective_date against an as-of date, country/jurisdiction scoping,
excluding non-normative clauses from being cited as authority) needs them
attached at the piece level, not re-looked-up from clause_id later.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from ingestion.chunker import chunk_corpus
from ingestion.logging_setup import get_logger
from ingestion.schema import Chunk
from ingestion.table_serializer import serialize_all_tables

_log = get_logger("ingestion.index_units")


@dataclass
class IndexableUnit:
    piece_id: str
    clause_id: str
    text: str
    source_file: str
    country: str
    doc_type: str
    normative: bool
    temporal_applicability: str | None
    effective_date: dt.date | None
    effective_date_unresolved: bool
    lineage_id: str | None
    supersedes: str | None
    superseded_by: str | None


def _unit_from_metadata(piece_id: str, clause: Chunk, text: str) -> IndexableUnit:
    m = clause.metadata
    return IndexableUnit(
        piece_id=piece_id,
        clause_id=m.clause_id,
        text=text,
        source_file=clause.source_file,
        country=m.country,
        doc_type=m.doc_type.value,
        normative=m.normative,
        temporal_applicability=m.temporal_applicability.value if m.temporal_applicability else None,
        effective_date=m.effective_date,
        effective_date_unresolved=m.effective_date_unresolved,
        lineage_id=m.lineage_id,
        supersedes=m.supersedes,
        superseded_by=m.superseded_by,
    )


def build_indexable_units(chunks: list[Chunk]) -> list[IndexableUnit]:
    """Turn a parsed corpus (list of Chunk) into the flat list of
    IndexableUnit both index builders should consume. Prose clauses go
    through the chunker (usually 1 unit per clause, per the measured-fact
    note in ingestion/chunker.py); table clauses go through the table
    serializer (1 unit per row)."""
    by_clause_id: dict[str, Chunk] = {c.metadata.clause_id: c for c in chunks}

    units: list[IndexableUnit] = []
    for piece in chunk_corpus(chunks):
        clause = by_clause_id[piece.clause_id]
        units.append(_unit_from_metadata(piece.piece_id, clause, piece.text))
    for row in serialize_all_tables(chunks):
        clause = by_clause_id[row.clause_id]
        units.append(_unit_from_metadata(row.piece_id, clause, row.text))

    _log.info("built %d indexable units from %d clauses", len(units), len(chunks))
    return units
