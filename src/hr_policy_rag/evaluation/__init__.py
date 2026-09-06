"""Frozen evaluation contracts for retrieval quality gates."""

from hr_policy_rag.evaluation.provenance import canonical_text_sha256
from hr_policy_rag.evaluation.retrieval_cases import (
    RetrievalCase,
    RetrievalCaseSet,
    RetrievalSplit,
    RetrievalThresholds,
    load_retrieval_case_set,
)
from hr_policy_rag.evaluation.retrieval_metrics import (
    RetrievalAggregate,
    RetrievalCaseScore,
    RetrievalEvaluationMode,
    RetrievalEvaluationReport,
    aggregate_scores,
    passes_thresholds,
    score_case,
)

__all__ = [
    "RetrievalAggregate",
    "RetrievalCase",
    "RetrievalCaseScore",
    "RetrievalCaseSet",
    "RetrievalEvaluationMode",
    "RetrievalEvaluationReport",
    "RetrievalSplit",
    "RetrievalThresholds",
    "aggregate_scores",
    "canonical_text_sha256",
    "load_retrieval_case_set",
    "passes_thresholds",
    "score_case",
]
