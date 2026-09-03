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