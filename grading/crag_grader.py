"""
T-4.1: CRAG-style sufficiency grading over a HybridRetriever result.

Finding 1 (slot4_architecture_findings.md) is what this module exists to
encode: a grader that only asks "is there a relevant clause" repeats the
naive-RAG failure the P-01/P-02 straddle probes are designed to catch --
it would call retrieval SUFFICIENT for a SEGMENTED_ACCRUAL case even when
only one of the two versions needed to compute the split-and-sum survived
retrieval's as-of resolution (retrieval/filters.py's select_current_as_of
deliberately collapses each lineage to the single version in force on the
as-of date -- correct for POINT_IN_TIME, but exactly the wrong thing for
SEGMENTED_ACCRUAL/ELECTIVE, which need multiple versions of the same
lineage simultaneously). So sufficiency here is two separate tests, both
of which must pass:

  1. Relevance -- at least one NORMATIVE piece was retrieved at all.
     (normative:false illustrations/decoys must never be treated as
     satisfying a query on their own -- see D-2/MER-IN-GRATUITY-ILLUSTRATION.)

  2. Applicability completeness (Finding 1) -- for every retrieved
     normative piece that carries a temporal_applicability class, the
     FACTS that class needs to be *applied*, not just the clause's own
     text, must also be present in the retrieved set:
       - POINT_IN_TIME: the resolved version's effective_date must be
         known (not the deliberate R-09 unresolved case).
       - SEGMENTED_ACCRUAL / ELECTIVE: more than one version of that
         clause's lineage_id must be present among the retrieved pieces
         -- otherwise the segments/alternatives can't be computed at all,
         only guessed at. Under the standard retrieve() path this is
         ALWAYS true on a straddle query, by construction of
         select_current_as_of -- that's not a bug in this grader, it's
         the corrective re-query's reason to exist (T-4.2): re-retrieve
         that lineage_id without as-of collapsing.
       - GRANDFATHERED: the cohort test itself (IndexableUnit.cohort_rule)
         must be present on the retrieved piece -- a grandfathered clause
         without its cohort_rule text is a clause you can't apply, only
         quote.

This module does not decide whether a clause is topically ON-TOPIC for a
free-text query (that judgement already happened at rerank -- T-3.5) --
it decides whether what's on-topic is COMPLETE enough to reason over.
That split keeps this grader rule-based and deterministic (no LLM call,
no network, every branch unit-testable against real corpus fixtures)
rather than reaching for an LLM-as-judge the way CRAG's original paper
grades per-document relevance -- there is nothing here that needs a
judgment call an LLM would make differently; it's a completeness check
against a metadata contract the ingestion schema already enforces.
"""

from __future__ import annotations

from collections import defaultdict

from grading.schema import GradeVerdict, MissingReason, SufficiencyResult
from ingestion.logging_setup import get_logger
from ingestion.schema import TemporalApplicability
from retrieval.hybrid_search import RetrievedPiece

_log = get_logger("grading.crag_grader")

# Applicability classes that need more than the resolved-current version
# to be reasoned over correctly (Finding 1).
_MULTI_VERSION_CLASSES = {TemporalApplicability.SEGMENTED_ACCRUAL, TemporalApplicability.ELECTIVE}


def grade_sufficiency(pieces: list[RetrievedPiece]) -> SufficiencyResult:
    """Pure function over an already-retrieved piece list -- no I/O, no
    network, no LLM call. Takes the *rule-based* grading approach the
    module docstring argues for; there is deliberately no MockGrader /
    RealGrader split the way embedder.py and reranker.py have one,
    because there is no external model call here to mock."""

    normative = [p for p in pieces if p.unit.normative]
    if not normative:
        _log.info("grade_sufficiency: no normative pieces retrieved -> INSUFFICIENT")
        return SufficiencyResult(
            verdict=GradeVerdict.INSUFFICIENT,
            reasons=[MissingReason.NO_RELEVANT_CLAUSE],
            detail=["no normative clause was retrieved for this query"],
        )

    by_lineage: dict[str, list[RetrievedPiece]] = defaultdict(list)
    for p in normative:
        if p.unit.lineage_id is not None:
            by_lineage[p.unit.lineage_id].append(p)

    reasons: list[MissingReason] = []
    detail: list[str] = []

    for p in normative:
        applicability = p.unit.temporal_applicability
        if applicability is None:
            continue  # untracked lineage (no version history) -- nothing to complete

        if applicability == TemporalApplicability.POINT_IN_TIME.value:
            if p.unit.effective_date_unresolved:
                reasons.append(MissingReason.MISSING_EFFECTIVE_DATE)
                detail.append(f"{p.clause_id}: effective_date is deliberately unresolved (R-09)")
            elif p.unit.effective_date is None:
                reasons.append(MissingReason.MISSING_EFFECTIVE_DATE)
                detail.append(f"{p.clause_id}: POINT_IN_TIME clause has no effective_date")

        elif applicability in (tc.value for tc in _MULTI_VERSION_CLASSES):
            # Real corpus finding (caught writing this grader, not before):
            # SEGMENTED_ACCRUAL is used for two different things in the
            # corpus, and only one of them needs a sibling version fetched.
            # DIFC-L2-2019-DEWS/DIFC-EOSB-LEGACY-GRATUITY and
            # MER-IN-LEAVE-ANNUAL-V1/V2 are true amendment-boundary splits
            # -- both carry supersedes/superseded_by pointing at each
            # other, and BOTH versions must be present to split-and-sum.
            # DIFC-L2-2019-LEAVE ("accruing proportionately") has neither
            # field: it's a single clause whose rate prorates within a
            # year, with no amendment history at all -- flagging it
            # insufficient and trying to fetch a nonexistent sibling
            # would be a bug, not a correction. supersedes/superseded_by
            # is therefore the discriminator, not temporal_applicability
            # alone.
            is_amendment_pair = p.unit.supersedes is not None or p.unit.superseded_by is not None
            if is_amendment_pair:
                lineage = p.unit.lineage_id
                versions_present = by_lineage.get(lineage, []) if lineage else [p]
                distinct_clause_ids = {v.clause_id for v in versions_present}
                if len(distinct_clause_ids) < 2:
                    reasons.append(MissingReason.MISSING_SEGMENT_VERSIONS)
                    detail.append(
                        f"{p.clause_id}: {applicability} clause, only {len(distinct_clause_ids)} "
                        f"version(s) of lineage '{lineage}' retrieved -- segments/alternatives "
                        "can't be computed from one version alone"
                    )

        elif applicability == TemporalApplicability.GRANDFATHERED.value:
            if not p.unit.cohort_rule:
                reasons.append(MissingReason.MISSING_COHORT_RULE)
                detail.append(f"{p.clause_id}: GRANDFATHERED clause retrieved without its cohort_rule")

    if reasons:
        _log.info("grade_sufficiency: INSUFFICIENT (%s)", [r.value for r in reasons])
        return SufficiencyResult(verdict=GradeVerdict.INSUFFICIENT, reasons=reasons, detail=detail)

    _log.info("grade_sufficiency: SUFFICIENT (%d normative pieces)", len(normative))
    return SufficiencyResult(verdict=GradeVerdict.SUFFICIENT)
