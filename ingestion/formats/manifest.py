"""
Sidecar manifest format for non-markdown corpus documents.

This is the honest design answer to "real documents don't carry
'clause_id: ...' metadata blocks inside them like the markdown corpus
does." A real PDF or Word policy document has no structured metadata
embedded in its text -- in a real org, that metadata (effective date,
country, version) lives somewhere else: a document-management system's
properties, a tracking spreadsheet, or (per this project's own Phase 6
plan) Google Drive file properties. So a non-markdown source document gets
a companion `<document>.manifest.json` file next to it, holding exactly
the same ChunkMetadata fields the markdown parser reads inline, plus a
`locator` telling the format-specific parser where in the source document
each clause's text actually is (a page range for PDF, a paragraph range
for DOCX, a row range for a spreadsheet).

This keeps ingestion.schema.ChunkMetadata as the single validated shape
every format ultimately produces -- the manifest is just a different place
to read the same fields FROM, not a different schema.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_manifest(path: Path) -> list[dict]:
    """Load a manifest file: a JSON array of clause entries, each a dict
    with at least 'clause_id' and 'locator', plus whatever ChunkMetadata
    fields apply (country, doc_type, effective_date, temporal_applicability,
    normative, ...). Raises ValueError on structural problems -- deliberately
    strict, since a manifest with a missing locator silently produces an
    empty or wrong clause rather than an obvious error."""
    if not path.exists():
        raise ValueError(f"manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: manifest must be a JSON array of clause entries")
    for i, entry in enumerate(data):
        if "clause_id" not in entry:
            raise ValueError(f"{path}[{i}]: manifest entry missing 'clause_id'")
        if "locator" not in entry:
            raise ValueError(f"{path}[{i}]: manifest entry missing 'locator'")
    return data
