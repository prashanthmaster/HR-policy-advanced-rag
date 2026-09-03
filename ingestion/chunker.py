"""
T-2.3: clause-aware chunker.

Hard rule (FM-D2, and the concrete example the project keeps citing --
MER-IN-GRATUITY-FORFEITURE / IN-GRAT-S4-6-FORFEITURE): a clause's operative
provisos must never end up in a different retrieval piece than the rule
they qualify. "Fifteen days' wages per year, PROVIDED that where the
termination is for riotous conduct the gratuity is wholly or partially
forfeited" is one legal unit. A naive fixed-length splitter that cuts
between the base rule and its proviso would let a generator answer from
the base rule alone and hand someone a number the law does not actually
support.

Measured reality of this corpus (checked 3 Sep 2026): the longest clause
body is 1,111 characters (IN-GRAT-S4-6-FORFEITURE); the median is 357.
DEFAULT_MAX_CHARS is set well above that, so in practice every clause in
today's 72-clause corpus comes back as a single, unsplit piece. This
module exists for clauses that don't fit that pattern yet (a future
document with a genuinely long clause), and is tested against a
deliberately long synthetic fixture, not just against the current corpus
where the rule never actually fires -- a chunker that has never been
exercised is not a chunker anyone should trust.

Splitting strategy: split the body into sentence-like units, then merge any
unit that opens with a proviso marker ("provided that", "provided
further", "PROVIDED") into the unit before it -- so "rule + all its
provisos" is one atomic group that is never cut apart. Atomic groups are
then greedily packed into pieces under max_chars. If a single atomic group
itself exceeds max_chars, it is kept whole anyway and becomes an
oversized piece: correctness (never split a proviso from its rule) wins
over neatness (every piece under the nominal limit).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ingestion.logging_setup import get_logger
from ingestion.schema import Chunk

_log = get_logger("ingestion.chunker")

DEFAULT_MAX_CHARS = 1600

# Sentence boundary: a period/semicolon followed by whitespace and a
# capital letter or digit (keeps "26) x 15" style formulas from being cut,
# since those don't have a capital/digit immediately after the space in a
# way that looks like a new sentence... in practice this is a heuristic,
# not a real sentence tokenizer, and is documented as such rather than
# oversold.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.;])\s+(?=[A-Z(])")

_PROVISO_RE = re.compile(
    r"^\s*(provided (that|further)|PROVIDED)\b", re.IGNORECASE
)


@dataclass
class ChunkPiece:
    """One retrievable piece of a clause. For the overwhelming majority of
    clauses in this corpus, index_in_clause == 0 and total_pieces == 1 --
    i.e. the clause fit in one piece. piece_id is what actually gets
    embedded/indexed downstream; clause_id alone is not unique once a
    clause is split into more than one piece."""

    clause_id: str
    piece_id: str
    index_in_clause: int
    total_pieces: int
    text: str


def _split_into_atomic_groups(body: str) -> list[str]:
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(body) if s.strip()]
    if not sentences:
        return [body.strip()] if body.strip() else []

    groups: list[str] = [sentences[0]]
    for s in sentences[1:]:
        if _PROVISO_RE.match(s):
            groups[-1] = groups[-1] + " " + s
        else:
            groups.append(s)
    return groups


def chunk_clause(chunk: Chunk, *, max_chars: int = DEFAULT_MAX_CHARS) -> list[ChunkPiece]:
    """Split one Chunk's body into one or more ChunkPieces, respecting the
    proviso-integrity rule above. Table-stream clauses (chunk_stream ==
    'table') are NOT handled here -- see ingestion/table_serializer.py
    (T-2.4), which has its own, different, row-based splitting logic and
    should be used instead for those."""
    if chunk.metadata.chunk_stream.value == "table":
        raise ValueError(
            f"{chunk.metadata.clause_id}: chunk_stream is 'table' -- use "
            "ingestion.table_serializer, not chunk_clause(), for table clauses"
        )

    groups = _split_into_atomic_groups(chunk.body)
    if not groups:
        return []

    pieces_text: list[str] = []
    current: list[str] = []
    current_len = 0
    for g in groups:
        g_len = len(g) + (1 if current else 0)
        if current and current_len + g_len > max_chars:
            pieces_text.append(" ".join(current))
            current = [g]
            current_len = len(g)
        else:
            current.append(g)
            current_len += g_len
    if current:
        pieces_text.append(" ".join(current))

    if len(pieces_text) > 1:
        _log.info(
            "%s: split into %d pieces (body %d chars, max_chars %d)",
            chunk.metadata.clause_id, len(pieces_text), len(chunk.body), max_chars,
        )
    oversized = [p for p in pieces_text if len(p) > max_chars]
    for p in oversized:
        _log.warning(
            "%s: a piece is %d chars, over max_chars %d -- kept whole "
            "because splitting it would separate a rule from its proviso",
            chunk.metadata.clause_id, len(p), max_chars,
        )

    total = len(pieces_text)
    return [
        ChunkPiece(
            clause_id=chunk.metadata.clause_id,
            piece_id=chunk.metadata.clause_id if total == 1 else f"{chunk.metadata.clause_id}#p{i}",
            index_in_clause=i,
            total_pieces=total,
            text=text,
        )
        for i, text in enumerate(pieces_text)
    ]


def chunk_corpus(chunks: list[Chunk], *, max_chars: int = DEFAULT_MAX_CHARS) -> list[ChunkPiece]:
    """Chunk every non-table clause in a parsed corpus. Table-stream
    clauses are skipped here -- callers should route those through
    ingestion.table_serializer separately and combine the two lists."""
    pieces: list[ChunkPiece] = []
    for c in chunks:
        if c.metadata.chunk_stream.value == "table":
            continue
        pieces.extend(chunk_clause(c, max_chars=max_chars))
    return pieces
