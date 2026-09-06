"""Fail-closed parsers for serving corpus formats."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from hr_policy_rag.corpus import ManifestSource, SourceMediaType

MAX_PDF_CONTENT_STREAM_BYTES = 20_000_000
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_HORIZONTAL_WHITESPACE = re.compile(r"[ \t]+")


class IngestionError(RuntimeError):
    """Stable error raised instead of silently omitting unsafe content."""

    def __init__(self, code: str, source_id: str, detail: str) -> None:
        self.code = code
        self.source_id = source_id
        self.detail = detail
        super().__init__(f"{code} [{source_id}]: {detail}")


@dataclass(frozen=True, slots=True)
class ParsedUnit:
    locator: str
    section_path: tuple[str, ...]
    text: str
    page_number: int | None


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    units: tuple[ParsedUnit, ...]
    warnings: tuple[str, ...] = ()


class _MessageHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _canonical_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\ufb00", "ff").replace("\ufb01", "fi").replace("\ufb02", "fl")
    lines = [_HORIZONTAL_WHITESPACE.sub(" ", line).strip() for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _read_utf8(path: Path, source_id: str) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestionError("SOURCE_ENCODING_INVALID", source_id, str(exc)) from exc
    except OSError as exc:
        raise IngestionError("SOURCE_READ_FAILED", source_id, str(exc)) from exc


def _parse_atx_sections(source: ManifestSource, text: str) -> list[ParsedUnit]:
    headings: list[str] = []
    body: list[str] = []
    units: list[ParsedUnit] = []

    def flush() -> None:
        canonical = _canonical_text("\n".join(body))
        if canonical:
            section_path = tuple(headings) if headings else (source.title or source.source_id,)
            units.append(
                ParsedUnit(
                    locator=" > ".join(section_path),
                    section_path=section_path,
                    text=canonical,
                    page_number=None,
                )
            )
        body.clear()

    for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        match = _HEADING.match(line)
        if match is None:
            body.append(line)
            continue
        flush()
        level = len(match.group(1))
        heading = _canonical_text(match.group(2))
        headings[level - 1 :] = [heading]

    flush()
    return units


def _parse_clause_blocks(source: ManifestSource, text: str) -> list[ParsedUnit]:
    parts = text.split("\n---\n")
    if len(parts) < 3:
        if "clause_id:" in text:
            raise IngestionError("MARKDOWN_CLAUSE_BLOCK_INVALID", source.source_id, source.relative_path)
        return _parse_atx_sections(source, text)
    if len(parts) % 2 == 0:
        raise IngestionError("MARKDOWN_CLAUSE_BLOCK_INVALID", source.source_id, source.relative_path)

    units = _parse_atx_sections(source, parts[0])
    for index in range(1, len(parts), 2):
        metadata: dict[str, str] = {}
        for line in parts[index].splitlines():
            key, separator, value = line.partition(":")
            if separator:
                metadata[key.strip()] = value.strip()
        clause_id = metadata.get("clause_id")
        section = metadata.get("section")
        body = _canonical_text(parts[index + 1])
        if not clause_id or not section or not body:
            raise IngestionError("MARKDOWN_CLAUSE_BLOCK_INVALID", source.source_id, f"block {(index + 1) // 2}")
        clause_locator = f"Clause {clause_id} (section {section})"
        units.append(
            ParsedUnit(
                locator=clause_locator,
                section_path=(source.title or source.source_id, clause_locator),
                text=body,
                page_number=None,
            )
        )
    return units


def parse_markdown(source: ManifestSource, path: Path) -> ParsedDocument:
    text = _read_utf8(path, source.source_id)
    units = _parse_clause_blocks(source, text)
    if not units:
        raise IngestionError("TEXT_CONTENT_MISSING", source.source_id, source.relative_path)
    return ParsedDocument(units=tuple(units))


def _approved_pages(source: ManifestSource, page_count: int) -> tuple[int, ...]:
    pages = tuple(
        page
        for page_range in source.approved_page_ranges
        for page in range(page_range.start_page, page_range.end_page + 1)
    )
    if not pages or pages[-1] > page_count:
        raise IngestionError(
            "PDF_PAGE_RANGE_INVALID",
            source.source_id,
            f"approved pages {pages!r} outside 1..{page_count}",
        )
    return pages


def parse_pdf(source: ManifestSource, path: Path) -> ParsedDocument:
    logger = logging.getLogger("pypdf")
    message_handler = _MessageHandler()
    prior_propagate = logger.propagate
    logger.addHandler(message_handler)
    logger.propagate = False
    try:
        try:
            reader = PdfReader(path, strict=True)
        except (OSError, PdfReadError, ValueError) as exc:
            raise IngestionError("PDF_READ_FAILED", source.source_id, str(exc)) from exc
        if reader.is_encrypted:
            raise IngestionError("PDF_ENCRYPTED", source.source_id, source.relative_path)

        page_count = len(reader.pages)
        units: list[ParsedUnit] = []
        for page_number in _approved_pages(source, page_count):
            page = reader.pages[page_number - 1]
            try:
                contents = page.get_contents()
                stream_size = 0 if contents is None else len(contents.get_data())
                if stream_size > MAX_PDF_CONTENT_STREAM_BYTES:
                    raise IngestionError(
                        "PDF_PAGE_TOO_LARGE",
                        source.source_id,
                        f"page {page_number} content stream is {stream_size} bytes",
                    )
                text = "" if contents is None else _canonical_text(page.extract_text(extraction_mode="layout") or "")
            except IngestionError:
                raise
            except (KeyError, PdfReadError, ValueError) as exc:
                raise IngestionError("PDF_EXTRACTION_FAILED", source.source_id, f"page {page_number}: {exc}") from exc
            if not text:
                raise IngestionError("PDF_TEXT_MISSING", source.source_id, f"page {page_number}")
            locator = f"PDF page {page_number}"
            units.append(
                ParsedUnit(
                    locator=locator,
                    section_path=(source.title or source.source_id, locator),
                    text=text,
                    page_number=page_number,
                )
            )
        return ParsedDocument(units=tuple(units), warnings=tuple(dict.fromkeys(message_handler.messages)))
    finally:
        logger.removeHandler(message_handler)
        logger.propagate = prior_propagate


def parse_source(source: ManifestSource, path: Path) -> ParsedDocument:
    if source.media_type is SourceMediaType.MARKDOWN:
        return parse_markdown(source, path)
    if source.media_type is SourceMediaType.PDF:
        return parse_pdf(source, path)
    raise IngestionError("UNSUPPORTED_MEDIA_TYPE", source.source_id, source.media_type.value)
