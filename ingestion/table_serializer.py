"""
T-2.4: table serialization for chunk_stream == "table" clauses.

Only one clause in the current corpus needs this: MER-AE-HOUSING-TABLE
(R-16, probe P-30). The corpus already writes it "row-wise" -- each
grade/tenure-band combination is its own bullet line ("Grade M2, 3 to 5
years of service: 9,500 per month.") rather than a markdown pipe table --
per the authoring comment in that clause: embeddings do not reliably tell
"AED 8,000" from "AED 9,500" apart in near-identical rows, so BM25 plus
one-row-per-chunk is what actually lands the correct cell, not a bigger
embedding model.

What this module adds on top of that authoring choice: each bullet row
becomes its OWN retrieval piece (not one giant paragraph chunk for the
whole table), carrying the table's title and any trailing qualifying
prose (here: housing allowance excluded from EOS basic-wage) along with
it -- so a retriever that lands on a single row still has enough context
to answer correctly without needing the rest of the table.
"""

from __future__ import annotations

from dataclasses import dataclass

from ingestion.logging_setup import get_logger
from ingestion.schema import Chunk

_log = get_logger("ingestion.table_serializer")

_ROW_PREFIX = "- "


@dataclass
class TableRowPiece:
    clause_id: str
    piece_id: str
    row_index: int
    total_rows: int
    text: str


def _split_title_rows_trailer(body: str) -> tuple[str, list[str], str]:
    lines = body.splitlines()
    title_lines: list[str] = []
    rows: list[str] = []
    trailer_lines: list[str] = []

    i = 0
    while i < len(lines) and not lines[i].strip().startswith(_ROW_PREFIX):
        if lines[i].strip():
            title_lines.append(lines[i].strip())
        i += 1
    while i < len(lines) and lines[i].strip().startswith(_ROW_PREFIX):
        rows.append(lines[i].strip()[len(_ROW_PREFIX):].strip())
        i += 1
    while i < len(lines):
        if lines[i].strip():
            trailer_lines.append(lines[i].strip())
        i += 1

    return " ".join(title_lines), rows, " ".join(trailer_lines)


def serialize_table_clause(chunk: Chunk) -> list[TableRowPiece]:
    """Turn a chunk_stream=='table' Chunk into one TableRowPiece per row.
    Raises ValueError on a non-table chunk, or on a table clause with no
    bullet rows found (a real structural problem worth failing loudly on,
    not silently emitting zero pieces for)."""
    if chunk.metadata.chunk_stream.value != "table":
        raise ValueError(
            f"{chunk.metadata.clause_id}: chunk_stream is not 'table' -- "
            "use ingestion.chunker.chunk_clause() instead"
        )

    title, rows, trailer = _split_title_rows_trailer(chunk.body)
    if not rows:
        _log.error("%s: chunk_stream=table but no bullet rows found in body", chunk.metadata.clause_id)
        raise ValueError(
            f"{chunk.metadata.clause_id}: no bullet rows found -- expected "
            "lines starting with '- ' after the title"
        )

    _log.info("%s: serialized into %d row pieces", chunk.metadata.clause_id, len(rows))

    total = len(rows)
    pieces = []
    for i, row in enumerate(rows):
        parts = [p for p in (title, row, trailer) if p]
        pieces.append(
            TableRowPiece(
                clause_id=chunk.metadata.clause_id,
                piece_id=f"{chunk.metadata.clause_id}#row{i}",
                row_index=i,
                total_rows=total,
                text=" ".join(parts),
            )
        )
    return pieces


def serialize_all_tables(chunks: list[Chunk]) -> list[TableRowPiece]:
    """Serialize every chunk_stream=='table' clause in a parsed corpus."""
    pieces: list[TableRowPiece] = []
    for c in chunks:
        if c.metadata.chunk_stream.value == "table":
            pieces.extend(serialize_table_clause(c))
    return pieces
