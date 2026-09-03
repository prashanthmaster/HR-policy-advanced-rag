"""
PDF parser -- extracts clause text from a PDF by page range, per the
sidecar manifest's locator ({"page_start": N, "page_end": N}, 1-indexed
inclusive, matching how a human would describe "pages 2-3" of a document).

Uses pypdf's extract_text(), which is a real text-layer extraction (not
OCR) -- it will correctly read a PDF that has a genuine text layer (the
overwhelming majority of policy/law documents distributed as PDF), and
will NOT extract anything from a scanned image with no text layer. That
limitation is inherent to pypdf, not something this module works around;
a scanned/image-only PDF is out of scope here the same way vision/OCR is
out of scope for the whole project (see README's explicitly-out-of-scope
list).
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from ingestion.formats.manifest import load_manifest
from ingestion.logging_setup import get_logger
from ingestion.schema import Chunk, ChunkMetadata

_log = get_logger("ingestion.formats.pdf_parser")


def parse_pdf(pdf_path: Path, manifest_path: Path, *, repo_root: Path | None = None) -> list[Chunk]:
    reader = PdfReader(str(pdf_path))
    entries = load_manifest(manifest_path)
    source_file = str(pdf_path.relative_to(repo_root)) if repo_root else str(pdf_path)

    chunks: list[Chunk] = []
    for order, entry in enumerate(entries):
        locator = entry["locator"]
        page_start = locator["page_start"]
        page_end = locator["page_end"]
        if page_start < 1 or page_end > len(reader.pages) or page_start > page_end:
            raise ValueError(
                f"{manifest_path}: clause {entry['clause_id']!r} locator "
                f"page_start={page_start} page_end={page_end} out of range "
                f"for a {len(reader.pages)}-page PDF"
            )
        texts = [reader.pages[p - 1].extract_text() or "" for p in range(page_start, page_end + 1)]
        body = "\n".join(t.strip() for t in texts if t.strip()).strip()
        if not body:
            _log.error("%s: no extractable text on pages %d-%d (scanned/image PDF?)", entry["clause_id"], page_start, page_end)
            raise ValueError(
                f"{entry['clause_id']}: no extractable text on pages {page_start}-{page_end} "
                "-- pypdf reads a PDF's text layer only, not scanned images (out of scope, see README)"
            )

        metadata_fields = {k: v for k, v in entry.items() if k not in ("locator",)}
        metadata = ChunkMetadata.model_validate(metadata_fields)
        chunks.append(Chunk(metadata=metadata, body=body, source_file=source_file, order_in_file=order))

    _log.info("parsed %d clauses from PDF %s", len(chunks), pdf_path)
    return chunks
