"""Tests for grading/crag_grader.py (T-4.1), against the real corpus so
the fixtures used are the actual DIFC DEWS / India gratuity ceiling /
UAE grandfathered-supplement clauses, not synthetic stand-ins that could
drift from what the corpus actually says."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from grading.crag_grader import grade_sufficiency
from grading.schema import GradeVerdict, MissingReason
from ingestion.index_units import IndexableUnit, build_indexable_units
from ingestion.parser import parse_corpus
from retrieval.hybrid_search import RetrievedPiece

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


@pytest.fixture(scope="module")
def units() -> list[IndexableUnit]:
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    return build_indexable_units(chunks)


def _piece_for(units: list[IndexableUnit], clause_id: str) -> RetrievedPiece:
    unit = next(u for u in units if u.clause_id == clause_id)
    return RetrievedPiece(
        piece_id=unit.piece_id,
        clause_id=unit.clause_id,
        text=unit.text,
        fused_score=1.0,
        rerank_score=1.0,
        unit=unit,
    )


def test_no_normative_pieces_is_insufficient():
    result = grade_sufficiency([])
    assert result.verdict is GradeVerdict.INSUFFICIENT
    assert result.reasons == [MissingReason.NO_RELEVANT_CLAUSE]


def test_illustration_alone_does_not_satisfy_the_query(units):
    """D-2: MER-IN-GRATUITY-ILLUSTRATION is normative:false. A retrieval
    that surfaces only the worked example, with no normative clause,
    must not be graded SUFFICIENT -- Finding 1's relevance leg."""
    piece = _piece_for(units, "MER-IN-GRATUITY-ILLUSTRATION")
    assert piece.unit.normative is False
    result = grade_sufficiency([piece])
    assert result.verdict is GradeVerdict.INSUFFICIENT
    assert MissingReason.NO_RELEVANT_CLAUSE in result.reasons


def test_india_gratuity_ceiling_point_in_time_alone_is_sufficient(units):
    """P-01: the resolved (as-of-current) India gratuity ceiling clause is
    POINT_IN_TIME and self-contained -- one version is enough, unlike a
    SEGMENTED_ACCRUAL clause. select_current_as_of already resolved which
    version governs; the grader must not additionally demand the
    superseded version just because a lineage exists."""
    piece = _piece_for(units, "IN-GRAT-S4-CEILING")
    assert piece.unit.temporal_applicability == "POINT_IN_TIME"
    result = grade_sufficiency([piece])
    assert result.verdict is GradeVerdict.SUFFICIENT


def test_difc_dews_single_version_is_insufficient(units):
    """P-3a: DIFC-L2-2019-DEWS is SEGMENTED_ACCRUAL, lineage DIFC-EOSB,
    and needs its sibling DIFC-EOSB-LEGACY-GRATUITY (same lineage, the
    pre-2020-02-01 segment) to compute a straddling employee's total.
    Retrieval's normal as-of resolution collapses the lineage to this one
    version -- the grader must catch that, not wave it through."""
    piece = _piece_for(units, "DIFC-L2-2019-DEWS")
    assert piece.unit.temporal_applicability == "SEGMENTED_ACCRUAL"
    result = grade_sufficiency([piece])
    assert result.verdict is GradeVerdict.INSUFFICIENT
    assert MissingReason.MISSING_SEGMENT_VERSIONS in result.reasons


def test_segmented_accrual_without_amendment_pair_is_self_contained(units):
    """DIFC-L2-2019-LEAVE is SEGMENTED_ACCRUAL ("accruing proportionately")
    but carries neither supersedes nor superseded_by -- there is no
    sibling version to fetch, so one retrieved piece is already
    sufficient. Contrast with test_difc_dews_single_version_is_insufficient
    below, where supersedes/superseded_by IS set and a sibling really is
    missing."""
    piece = _piece_for(units, "DIFC-L2-2019-LEAVE")
    assert piece.unit.temporal_applicability == "SEGMENTED_ACCRUAL"
    assert piece.unit.supersedes is None
    assert piece.unit.superseded_by is None
    result = grade_sufficiency([piece])
    assert result.verdict is GradeVerdict.SUFFICIENT


def test_difc_dews_both_segments_present_is_sufficient(units):
    """Once corrective re-query (T-4.2) pulls in both lineage members,
    the same clause is sufficient."""
    dews = _piece_for(units, "DIFC-L2-2019-DEWS")
    legacy = _piece_for(units, "DIFC-EOSB-LEGACY-GRATUITY")
    assert dews.unit.lineage_id == legacy.unit.lineage_id == "DIFC-EOSB"
    result = grade_sufficiency([dews, legacy])
    assert result.verdict is GradeVerdict.SUFFICIENT


def test_grandfathered_clause_without_cohort_rule_is_insufficient(units):
    """P-06: the UAE end-of-service supplement is GRANDFATHERED and
    carries cohort_rule='service_commenced_before(2025-01-01)' in the
    real corpus -- this test would fail (correctly) if that metadata
    were ever stripped."""
    piece = _piece_for(units, next(
        u.clause_id for u in units if u.cohort_rule is not None
    ))
    assert piece.unit.temporal_applicability == "GRANDFATHERED"
    assert piece.unit.cohort_rule

    result = grade_sufficiency([piece])
    assert result.verdict is GradeVerdict.SUFFICIENT

    stripped = RetrievedPiece(
        piece_id=piece.piece_id,
        clause_id=piece.clause_id,
        text=piece.text,
        fused_score=1.0,
        rerank_score=1.0,
        unit=IndexableUnit(**{**piece.unit.__dict__, "cohort_rule": None}),
    )
    stripped_result = grade_sufficiency([stripped])
    assert stripped_result.verdict is GradeVerdict.INSUFFICIENT
    assert MissingReason.MISSING_COHORT_RULE in stripped_result.reasons


def test_synthetic_elective_pair_needs_both_alternatives():
    """No real ELECTIVE fixture exists in the corpus yet (Finding 1 names
    the class; nothing currently exercises it) -- this exercises the
    class generically via a synthetic pair so the branch isn't dead code
    with zero coverage."""

    def _unit(clause_id: str) -> IndexableUnit:
        return IndexableUnit(
            piece_id=clause_id,
            clause_id=clause_id,
            text=f"text for {clause_id}",
            source_file="fixture.md",
            country="India",
            doc_type="policy",
            jurisdiction_scope=None,
            normative=True,
            temporal_applicability="ELECTIVE",
            effective_date=dt.date(2020, 1, 1),
            effective_date_unresolved=False,
            lineage_id="LIN-ELECTIVE",
            supersedes=None if clause_id == "a" else "a",
            superseded_by="b" if clause_id == "a" else None,
        )

    one = RetrievedPiece(
        piece_id="a", clause_id="a", text="a", fused_score=1.0, rerank_score=1.0, unit=_unit("a")
    )
    result_one = grade_sufficiency([one])
    assert result_one.verdict is GradeVerdict.INSUFFICIENT
    assert MissingReason.MISSING_SEGMENT_VERSIONS in result_one.reasons  # same reason code covers ELECTIVE

    two = RetrievedPiece(
        piece_id="b", clause_id="b", text="b", fused_score=1.0, rerank_score=1.0, unit=_unit("b")
    )
    result_two = grade_sufficiency([one, two])
    assert result_two.verdict is GradeVerdict.SUFFICIENT
