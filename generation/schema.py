from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass
class Citation:
    clause_id: str
    doc: str
    section: str | None
    version: str | None
    effective_date: dt.date | None


@dataclass
class GeneratedAnswer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    used_temporal_reasoning: bool = False
    computed_amount: float | None = None
    """Phase 5 addition (generation/formula.py): a rupee (or equivalent)
    figure, only ever set when a real formula match AND the needed
    ServiceFacts (dates, wage) were all present -- None means the system
    is not asserting a number, never a silently-wrong default."""
    computed_days: float | None = None
    """Same rule as computed_amount, for a day-count figure (leave
    accrual, or a currency-agnostic tenure-banded total like UAE's
    gratuity days where no verified wage-per-day convention exists)."""
    superseded_warning: str | None = None
    """T-4.6/FM-E6: set when a cited clause has been superseded and its
    replacement is NOT also part of this answer -- a stale-citation
    safety net. None when nothing is stale (the normal case, and also
    the legitimate SEGMENTED_ACCRUAL case where both old and new
    versions are cited together on purpose)."""