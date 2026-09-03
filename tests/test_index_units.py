"""Tests for ingestion/index_units.py -- the unified prose+table indexable-unit list."""

from __future__ import annotations

from pathlib import Path

from ingestion.index_units import build_indexable_units
from ingestion.parser import parse_corpus

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"


def test_units_cover_prose_and_table_clauses():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)

    # 71 non-table clauses (each 1 unit, per the measured-fact chunker test)
    # + 13 housing-table rows = 84.
    assert len(units) == 84

    housing_rows = [u for u in units if u.clause_id == "MER-AE-HOUSING-TABLE"]
    assert len(housing_rows) == 13


def test_unit_carries_filtering_metadata():
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)
    ceiling = next(u for u in units if u.clause_id == "IN-GRAT-S4-CEILING")
    assert ceiling.country == "India"
    assert ceiling.temporal_applicability == "POINT_IN_TIME"
    assert ceiling.normative is True

    illustration = next(u for u in units if u.clause_id == "MER-IN-GRATUITY-ILLUSTRATION")
    assert illustration.normative is False


def test_unit_carries_citation_and_cohort_fields():
    """Phase 4 gap: version/section/source_doc/source_act/source_url/cohort_rule
    were sitting in ChunkMetadata's model_extra but never propagated onto
    IndexableUnit -- the same class of gap T-3.2 caught for jurisdiction_scope.
    Generation (T-4.4) needs doc/section/version/effective_date for citations;
    the temporal reasoner (T-4.3) needs cohort_rule for the GRANDFATHERED class."""
    chunks = parse_corpus(CORPUS_DIR, repo_root=REPO_ROOT)
    units = build_indexable_units(chunks)

    ceiling = next(u for u in units if u.clause_id == "IN-GRAT-S4-CEILING")
    assert ceiling.section is not None
    assert ceiling.source_act is not None

    grandfathered = next(u for u in units if u.cohort_rule is not None)
    assert "service_commenced_before" in grandfathered.cohort_rule
