"""
Application logging + structured error collection for the ingestion pipeline.

This is the "basic logging" layer discussed with Prashanth on 3 Sep 2026 —
deliberately separate from LangSmith tracing (Phase 3+, once an LLM/
retrieval chain exists to trace) and separate from eval/coverage_audit.py
(checks the corpus data itself, not a running process). This module covers
the failure class those two don't: a Python exception in the parser, a
file-system or auth error, anything that happens before any LLM call.

Two things live here:
1. get_logger() -- a standard, consistently-configured logger. Every module
   in ingestion/ should get its logger from here, not call
   logging.getLogger(__name__) directly, so the format/handlers stay in one
   place.
2. ErrorCollector -- lets a batch operation (e.g. parsing every file in the
   corpus) keep going past a single bad item instead of dying on the first
   one, while still recording every failure with enough detail to act on.
   This is the "--keep-going" mode ingestion/parser.py's docstring already
   promised in T-2.1 -- implemented here rather than as a parser-specific
   flag, so change_kind.py, chunker.py, and the future index builders can
   all use the same collect-and-continue pattern instead of each inventing
   their own.

Design choice: logs go to BOTH the console (so a person watching a run sees
it live) and a file under logs/ (so a run that happened unattended, or
scheduled, leaves a record someone can come back to -- this project runs in
short device_bash calls with no persistent terminal, so "watch it happen"
is not always available). The file is append-only and one per day, not one
per run, so a day's worth of iteration doesn't scatter across dozens of
files.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_CONFIGURED = False


def _ensure_configured() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _LOG_DIR.mkdir(exist_ok=True)
    log_file = _LOG_DIR / f"{date.today().isoformat()}.log"

    root = logging.getLogger("hrpolicy")
    root.setLevel(logging.DEBUG)
    root.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)  # console stays readable; file gets everything
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the shared 'hrpolicy' namespace. name should be
    the calling module's own name (e.g. 'ingestion.parser') so log lines
    show where they came from."""
    _ensure_configured()
    return logging.getLogger(f"hrpolicy.{name}")


@dataclass
class CollectedError:
    """One failure recorded by an ErrorCollector run. item_id should be
    whatever identifies the thing that failed to a human reading the log
    later -- a file path, a clause_id, a probe id -- not a generic index."""

    item_id: str
    error_type: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


class ErrorCollector:
    """Collects failures from a batch operation instead of raising on the
    first one, so e.g. one malformed corpus file doesn't hide problems in
    the other 71 clauses. Use as:

        collector = ErrorCollector(logger)
        for item in items:
            with collector.item(item.id):
                risky_operation(item)
        if collector.had_errors:
            ...decide what to do...

    Every failure is logged immediately (so it's visible in real time and in
    the day's log file) AND recorded in .errors for the caller to act on
    programmatically (e.g. fail CI, print a summary table) -- logging alone
    is not enough because a log line scrolls past; the caller needs
    structured access to "did anything fail, and what."
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self.errors: list[CollectedError] = []

    def record(self, item_id: str, exc: BaseException, **context: Any) -> None:
        err = CollectedError(
            item_id=item_id,
            error_type=type(exc).__name__,
            message=str(exc),
            context=context,
        )
        self.errors.append(err)
        self._logger.error(
            "FAILED %s: %s: %s%s",
            item_id,
            err.error_type,
            err.message,
            f" (context={context})" if context else "",
        )

    def item(self, item_id: str, **context: Any) -> "_ItemContext":
        return _ItemContext(self, item_id, context)

    @property
    def had_errors(self) -> bool:
        return bool(self.errors)

    def summary(self) -> str:
        if not self.errors:
            return "no errors"
        lines = [f"{len(self.errors)} error(s):"]
        for e in self.errors:
            lines.append(f"  - {e.item_id}: {e.error_type}: {e.message}")
        return "\n".join(lines)


class _ItemContext:
    """Context manager returned by ErrorCollector.item(). Swallows
    exceptions raised inside the `with` block, recording them on the
    collector, and lets the surrounding loop continue to the next item.
    Deliberately does NOT catch BaseException-level things like
    KeyboardInterrupt/SystemExit -- only Exception and its subclasses, so a
    genuine "stop everything" signal still stops everything."""

    def __init__(self, collector: ErrorCollector, item_id: str, context: dict[str, Any]):
        self._collector = collector
        self._item_id = item_id
        self._context = context

    def __enter__(self) -> "_ItemContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            return False
        if not isinstance(exc, Exception):
            return False  # let KeyboardInterrupt / SystemExit propagate
        self._collector.record(self._item_id, exc, **self._context)
        return True  # suppress -- caller's loop continues
