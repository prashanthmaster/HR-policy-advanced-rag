"""T-6.5 tests: clause-level version-event detection (Option B -- flag,
never auto-decide supersession). Uses hand-built Chunk fixtures, not the
real corpus, since these tests are about the diff/classification logic,
not about any specific clause's real content."""

from __future__ import annotations

import datetime as dt

from ingestion.change_kind import ChangeKind
from ingestion.schema import Chunk, ChunkMetadata, DocType, TemporalApplicability
from drive_sync.version_events import detect_version_events


def _chunk(clause_id: str, body: str, source_file: str = "corpus/tier1_law/india/india_law.md") -> Chunk:
    return Chunk(
        metadata=ChunkMetadata(
            clause_id=clause_id,
            country="India",
            doc_type=DocType.LAW,
            effective_date=dt.date(2020, 1, 1),
            temporal_applicability=TemporalApplicability.POINT_IN_TIME,
        ),
        body=body,
        source_file=source_file,
        order_in_file=0,
    )


def test_no_events_when_nothing_changed():
    old = [_chunk("A", "Notice period is thirty days.")]
    new = [_chunk("A", "Notice period is thirty days.")]
    assert detect_version_events(old, new) == []


def test_no_events_for_editorial_only_change():
    old = [_chunk("A", "Notice period is thirty days, payable in lieu.")]
    new = [_chunk("A", "Notice period is thirty days payable in lieu")]
    assert detect_version_events(old, new) == []


def test_substantive_change_flagged_for_review():
    old = [_chunk("A", "Eligibility requires five years of continuous service.")]
    new = [_chunk("A", "Eligibility requires four years of continuous service.")]
    events = detect_version_events(old, new)
    assert len(events) == 1
    ev = events[0]
    assert ev.clause_id == "A"
    assert ev.kind == ChangeKind.SUBSTANTIVE
    assert ev.needs_human_review is True
    assert ev.note  # a real explanatory note, not blank
    assert ev.old_body != ev.new_body


def test_sunset_when_clause_removed_flagged_for_review():
    old = [_chunk("A", "Some clause text."), _chunk("B", "Another clause.")]
    new = [_chunk("B", "Another clause.")]
    events = detect_version_events(old, new)
    assert len(events) == 1
    assert events[0].clause_id == "A"
    assert events[0].kind == ChangeKind.SUNSET
    assert events[0].needs_human_review is True
    assert events[0].new_body is None


def test_addition_when_new_clause_id_appears_flagged_for_review():
    old = [_chunk("A", "Some clause text.")]
    new = [_chunk("A", "Some clause text."), _chunk("B", "Brand new clause.")]
    events = detect_version_events(old, new)
    assert len(events) == 1
    assert events[0].clause_id == "B"
    assert events[0].kind == ChangeKind.ADDITION
    assert events[0].needs_human_review is True
    assert events[0].old_body is None


def test_never_writes_supersession_fields_itself():
    # Option B guardrail: even on a SUBSTANTIVE change, this module must
    # never touch/return anything that looks like it decided a
    # supersedes/superseded_by/effective_date value -- it only classifies
    # and explains, per Prashanth's confirmed design choice (4 Sep 2026).
    old = [_chunk("A", "five years")]
    new = [_chunk("A", "four years")]
    ev = detect_version_events(old, new)[0]
    field_names = {f for f in vars(ev)}
    assert "supersedes" not in field_names
    assert "superseded_by" not in field_names
    assert "effective_date" not in field_names


def test_multiple_documents_worth_of_clauses_only_compares_matching_ids():
    old = [_chunk("A", "old text A"), _chunk("C", "unrelated, unchanged")]
    new = [_chunk("A", "new text A"), _chunk("C", "unrelated, unchanged")]
    events = detect_version_events(old, new)
    assert len(events) == 1
    assert events[0].clause_id == "A"
