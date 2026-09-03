"""
Tests for the T-2.1-addendum logging/error-collection layer added 3 Sep 2026
after the "is basic logging enough" conversation. Covers: a batch parse
survives one bad file instead of dying on it, every failure is both logged
and recorded structurally, and a day's log file actually gets written.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ingestion.logging_setup import ErrorCollector, get_logger
from ingestion.parser import parse_corpus_collecting


def test_error_collector_continues_past_failing_items():
    log = get_logger("test")
    collector = ErrorCollector(log)
    processed = []
    for item in ["a", "BAD", "c"]:
        with collector.item(item):
            if item == "BAD":
                raise ValueError("simulated failure")
            processed.append(item)
    assert processed == ["a", "c"]
    assert collector.had_errors
    assert len(collector.errors) == 1
    assert collector.errors[0].item_id == "BAD"
    assert collector.errors[0].error_type == "ValueError"


def test_error_collector_does_not_swallow_keyboard_interrupt():
    log = get_logger("test")
    collector = ErrorCollector(log)
    raised = False
    try:
        with collector.item("x"):
            raise KeyboardInterrupt()
    except KeyboardInterrupt:
        raised = True
    assert raised, "KeyboardInterrupt must propagate, not be swallowed as a normal error"
    assert not collector.errors


def test_parse_corpus_collecting_survives_one_bad_file(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    good = corpus_dir / "good.md"
    good.write_text(
        "# Good file\n\n"
        "---\n"
        "clause_id: X-1\n"
        "country: India\n"
        "doc_type: policy\n"
        "effective_date: 2024-01-01\n"
        "temporal_applicability: POINT_IN_TIME\n"
        "---\n"
        "A perfectly normal clause.\n"
    )

    bad = corpus_dir / "bad.md"
    bad.write_text(
        "# Bad file\n\n"
        "---\n"
        "clause_id: X-2\n"
        "country: Narnia\n"  # not a real country -> ValidationError
        "doc_type: policy\n"
        "effective_date: 2024-01-01\n"
        "temporal_applicability: POINT_IN_TIME\n"
        "---\n"
        "This clause will never validate.\n"
    )

    chunks, collector = parse_corpus_collecting(corpus_dir, repo_root=tmp_path)

    # The good file's clause must still come through even though bad.md failed.
    assert len(chunks) == 1
    assert chunks[0].metadata.clause_id == "X-1"

    assert collector.had_errors
    assert len(collector.errors) == 1
    assert "bad.md" in collector.errors[0].item_id


def test_logging_writes_to_todays_log_file():
    log = get_logger("test.file_write")
    log.error("test-marker-for-log-file-assertion")

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    from datetime import date

    log_file = log_dir / f"{date.today().isoformat()}.log"
    assert log_file.exists()
    assert "test-marker-for-log-file-assertion" in log_file.read_text(encoding="utf-8")
