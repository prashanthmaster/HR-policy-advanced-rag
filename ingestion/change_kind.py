"""
T-2.5: change-kind classifier.

The freshness/versioning differentiator (Phase 6) needs to tell a real
amendment apart from a typo fix before it fires a "this document changed"
event -- otherwise re-indexing on every Drive save, including ones that
fixed a comma, would flood the system with false version events and erode
trust in the ones that matter. This module is the rule-based first pass.

Categories (docs/FAILURE_MODES.md, Part 1):
- NO_OP: text is byte-identical. Nothing to classify, but exposed as a
  first-class outcome rather than silently skipped, so a caller can log
  "checked, no change" distinctly from "didn't check."
- EDITORIAL: text differs, but only in whitespace, punctuation, or case --
  a typo/formatting fix. Should NOT create a version event.
- SUBSTANTIVE: the operative wording changed -- a number, a date, an
  obligation. MUST create a version event.
- ADDITION: there was no prior text (old is None) -- a new clause.
- SUNSET: there was prior text and now there is none (new is None), or the
  new text is explicitly marked withdrawn/repealed.

Honesty note, per this project's ground rule on unverified claims: this is
a heuristic text classifier, not a legal-diff engine. It has NOT been
measured against real Google Drive edit history (Phase 6 doesn't exist
yet) -- SUBSTANTIVE vs EDITORIAL is decided by comparing normalized text,
which will correctly catch "15 days" -> "30 days" but could plausibly
misclassify a wording change that alters legal meaning without changing
any digit (e.g. "may" -> "shall"). That is a known, documented limitation,
not a claimed capability. Anything this function calls SUBSTANTIVE should
still go through the same human/LLM review a version event would already
get -- it is a triage step, not a final legal determination.
"""

from __future__ import annotations

import re
from enum import Enum

from ingestion.logging_setup import get_logger

_log = get_logger("ingestion.change_kind")

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[.,;:!?()\[\]\"'‘’“”–—-]")

_WITHDRAWN_MARKERS = ("withdrawn", "repealed", "revoked", "rescinded")


class ChangeKind(str, Enum):
    NO_OP = "NO_OP"
    EDITORIAL = "EDITORIAL"
    SUBSTANTIVE = "SUBSTANTIVE"
    ADDITION = "ADDITION"
    SUNSET = "SUNSET"


def _normalize(text: str) -> str:
    t = _PUNCTUATION_RE.sub("", text.lower())
    t = _WHITESPACE_RE.sub(" ", t).strip()
    return t


def classify_change(old_body: str | None, new_body: str | None) -> ChangeKind:
    """Classify the change between two versions of a clause's body text.
    old_body is what was previously indexed (None if the clause is new);
    new_body is the freshly read text (None if the clause is gone from the
    source document)."""
    if old_body is None and new_body is None:
        raise ValueError("classify_change: both old_body and new_body are None -- nothing to classify")

    if old_body is None:
        _log.info("classified as ADDITION (no prior text)")
        return ChangeKind.ADDITION

    if new_body is None:
        _log.info("classified as SUNSET (text removed)")
        return ChangeKind.SUNSET

    if any(marker in new_body.lower() for marker in _WITHDRAWN_MARKERS) and not any(
        marker in old_body.lower() for marker in _WITHDRAWN_MARKERS
    ):
        _log.info("classified as SUNSET (explicit withdrawal marker added)")
        return ChangeKind.SUNSET

    if old_body == new_body:
        return ChangeKind.NO_OP

    if _normalize(old_body) == _normalize(new_body):
        _log.info("classified as EDITORIAL (normalized text identical)")
        return ChangeKind.EDITORIAL

    _log.info("classified as SUBSTANTIVE (normalized text differs)")
    return ChangeKind.SUBSTANTIVE
