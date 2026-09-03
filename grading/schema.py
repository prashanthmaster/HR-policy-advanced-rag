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
