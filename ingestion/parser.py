"""
T-2.1: corpus markdown parser.

Turns a corpus/**/*.md file into a list of ingest.schema.Chunk objects.

Format this parses (established by the Phase-1 corpus files, not invented
here -- see corpus/tier1_law/*.md and corpus/tier2_policy/*/*.md):

    # Title
    intro prose, banners, "Build status" notes -- all ignored
    ---
    clause_id: FOO
    key: value
    ...
    ---
    body text, possibly containing an HTML comment block that documents a
    deliberate defect or a design rationale for the humans reading the file
    ---
    clause_id: BAR
    ...
    ---
    body text
    ---
    ## A markdown subheading with free prose -- ignored (e.g. the "Leave
    types covered by this chapter" section, or the "NOTE ON..." paragraphs)

A file is split on lines that are exactly `---` (optionally surrounded by
whitespace). That produces an alternating-ish sequence of segments; a
segment is a **metadata block** iff its first non-blank line matches
`clause_id: ...`. Every metadata block is paired with the segment that
follows it as that clause's body. Any segment that is not a metadata block,
and is not immediately preceded by one, is prose (title, banner, "NOTE ON
..." asides, subheadings) and is not part of any chunk.

Body text has its HTML comments stripped before being stored: comments are
authoring documentation (why a deliberate defect exists, cross-references
to the requirements/failure-mode docs) aimed at the next person editing the
corpus, not text a retrieval system should ever surface to an end user or
let an LLM read as if it were policy language. See docs/DELIBERATE_DEFECTS.md
-- the manifest entries themselves live in the comments; the *defect* is the
clause body outside the comment, and that's what gets indexed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ingestion.schema import Chunk, ChunkMetadata

_FENCE_RE = re.compile(r"^[ \t]*---[ \t]*$", re.MULTILINE)
_META_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_CLAUSE_ID_KEY = "clause_id"


class CorpusParseError(ValueError):
    """Raised for a structural problem in a corpus markdown file -- an
    unterminated metadata block, a metadata block with no body, a body with
    no preceding metadata block that looks like it was meant to be a clause
    (starts with what looks like a metadata line but is missing clause_id).
    Deliberately narrow: this is a parser, not a general markdown linter."""


@dataclass
class _Segment:
    text: str
    start_line: int  # 1-based line number of the segment's first line, for error messages


def _split_segments(raw: str) -> list[_Segment]:
    segments: list[_Segment] = []
    last_end = 0
    line_no = 1
    for m in _FENCE_RE.finditer(raw):
        chunk_text = raw[last_end : m.start()]
        segments.append(_Segment(text=chunk_text, start_line=line_no))
        line_no += chunk_text.count("\n") + 1
        last_end = m.end()
    tail = raw[last_end:]
    segments.append(_Segment(text=tail, start_line=line_no))
    return segments


def _looks_like_metadata_block(seg_text: str) -> bool:
    lines = [l for l in seg_text.strip("\n").splitlines() if l.strip()]
    if not lines:
        return False
    first = _META_LINE_RE.match(lines[0].strip())
    return bool(first and first.group(1) == _CLAUSE_ID_KEY)


def _parse_metadata_block(seg_text: str, *, source_file: str, line_no: int) -> dict:
    raw_fields: dict[str, str] = {}
    current_key: str | None = None
    for line in seg_text.strip("\n").splitlines():
        if not line.strip():
            continue
        m = _META_LINE_RE.match(line.strip())
        if m:
            current_key = m.group(1)
            raw_fields[current_key] = m.group(2).strip()
        elif current_key is not None:
            # Continuation of a wrapped value (rare, but don't silently drop it).
            raw_fields[current_key] += " " + line.strip()
        else:
            raise CorpusParseError(
                f"{source_file}:{line_no}: metadata block has a line that "
                f"isn't 'key: value' and isn't a continuation: {line!r}"
            )
    return raw_fields


_BOOL_TRUE = {"true", "yes"}
_BOOL_FALSE = {"false", "no"}


def _coerce_scalar_fields(raw_fields: dict[str, str]) -> dict:
    """Best-effort typing pass before handing to pydantic: booleans, so
    'normative: false' and 'normative: true' become real bools rather than
    the pydantic default (which would treat the non-empty string 'false' as
    truthy). Dates and enums are left as strings for pydantic to parse --
    pydantic's own date parsing already handles 'YYYY-MM-DD' correctly, and
    the one deliberate exception (UNRESOLVED) is handled in schema.py."""
    out: dict = dict(raw_fields)
    for key in ("normative", "effective_date_unresolved"):
        if key in out and isinstance(out[key], str):
            low = out[key].strip().lower()
            if low in _BOOL_TRUE:
                out[key] = True
            elif low in _BOOL_FALSE:
                out[key] = False
    return out


def parse_file(path: Path, *, repo_root: Path | None = None) -> list[Chunk]:
    """Parse one corpus markdown file into its clauses. Raises
    CorpusParseError on structural problems; raises pydantic's
    ValidationError (unchanged) on a metadata block that fails schema
    validation -- callers that want to keep going past a bad clause and
    collect all errors should catch per-file, not rely on this function to
    do that for them (see ingest/cli.py's --keep-going flag, T-2.8)."""
    raw = path.read_text(encoding="utf-8")
    source_file = str(path.relative_to(repo_root)) if repo_root else str(path)
    segments = _split_segments(raw)

    chunks: list[Chunk] = []
    order = 0
    i = 0
    while i < len(segments):
        seg = segments[i]
        if _looks_like_metadata_block(seg.text):
            if i + 1 >= len(segments):
                raise CorpusParseError(
                    f"{source_file}:{seg.start_line}: metadata block for a "
                    "clause is the last segment in the file -- it has no body"
                )
            body_seg = segments[i + 1]
            raw_fields = _parse_metadata_block(seg.text, source_file=source_file, line_no=seg.start_line)
            raw_fields = _coerce_scalar_fields(raw_fields)
            metadata = ChunkMetadata.model_validate(raw_fields)

            body = _HTML_COMMENT_RE.sub("", body_seg.text).strip()
            if not body:
                raise CorpusParseError(
                    f"{source_file}:{body_seg.start_line}: clause "
                    f"{metadata.clause_id!r} has an empty body after "
                    "stripping HTML comments -- the whole clause was "
                    "commentary, nothing normative was ever written"
                )

            chunks.append(
                Chunk(
                    metadata=metadata,
                    body=body,
                    source_file=source_file,
                    order_in_file=order,
                )
            )
            order += 1
            i += 2
        else:
            i += 1
    return chunks


def parse_corpus(corpus_dir: Path, *, repo_root: Path | None = None) -> list[Chunk]:
    """Parse every .md file under corpus_dir, in sorted path order (stable
    across OSes/filesystems, which matters for order_in_file/lineage
    debugging reproducibility)."""
    repo_root = repo_root or corpus_dir.parent
    chunks: list[Chunk] = []
    for md_path in sorted(corpus_dir.rglob("*.md")):
        chunks.extend(parse_file(md_path, repo_root=repo_root))
    return chunks
