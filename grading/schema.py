"""
Shared types for Phase 4's grading nodes (T-4.1 CRAG sufficiency,
T-4.3 temporal reasoning). Kept in their own module, same reason
ingestion/schema.py is separate from the parser -- generation (T-4.4) and
the eval harness (Phase 5) both need to import these types without
importing grading logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GradeVerdict(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"


class MissingReason(str, Enum):
    """Named, not free text, so the corrective re-query node (T-4.2) can
    branch on *why* grading failed rather than string-matching a reason
    sentence. Finding 1 is what NO_APPLICABILITY_RULE exists to encode:
    the trap is a grader that only checks "is there a relevant clause,"
    which is exactly the naive-RAG failure P-01/P-02 are designed to
    catch downstream of retrieval, not just at generation time."""

    NO_RELEVANT_CLAUSE = "no_relevant_clause"
    MISSING_EFFECTIVE_DATE = "missing_effective_date"
    MISSING_SEGMENT_VERSIONS = "missing_segment_versions"  # SEGMENTED_ACCRUAL and ELECTIVE both need >1 lineage version present
    MISSING_COHORT_RULE = "missing_cohort_rule"


@dataclass
class SufficiencyResult:
    verdict: GradeVerdict
    reasons: list[MissingReason] = field(default_factory=list)
    detail: list[str] = field(default_factory=list)
    """Human-readable detail, one entry per reason, e.g. which lineage_id
    is missing a segment. Never used for branching -- `reasons` is."""

    @property
    def is_sufficient(self) -> bool:
        return self.verdict is GradeVerdict.SUFFICIENT


# --- T-4.5: stateless clarification contract (Finding 5) ---------------


@dataclass
class MissingFact:
    fact: str
    """Short machine-stable name, e.g. "country", "service_start_date" --
    matches the strings T-4.3's TemporalWorking.missing_facts already
    uses, so the two layers speak the same vocabulary."""
    why: str
    """Human-readable explanation of why this fact is determinative --
    part of the contract, not decoration: Finding 5 requires the missing
    fact to come with its reason, not just its name."""


@dataclass
class ConditionalAnswer:
    condition: str
    """e.g. "if country = India" -- one branch per plausible value of
    the missing fact."""
    answer: "GeneratedAnswer"  # generation/schema.py -- string-annotated to avoid a circular import


@dataclass
class ClarificationResponse:
    """The whole point of Finding 5: this is returned as ONE terminal
    response in a single turn -- never a follow-up question that waits
    for a reply. The caller re-asks a self-contained question if they
    want a single answer; nothing here is remembered between turns."""

    status: str = "NEEDS_CLARIFICATION"
    missing_facts: list[MissingFact] = field(default_factory=list)
    conditional_answers: list[ConditionalAnswer] = field(default_factory=list)
