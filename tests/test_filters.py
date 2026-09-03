import datetime as dt

import pytest

from ingestion.index_units import IndexableUnit
from retrieval.filters import (
    apply_hard_filters,
    dedup_by_lineage,
    filter_by_country,
    filter_by_jurisdiction_scope,
    select_current_as_of,
)


def _unit(
    piece_id,
    country="India",
    jurisdiction_scope=None,
    lineage_id=None,
    effective_date=None,
    effective_date_unresolved=False,
):
    return IndexableUnit(
        piece_id=piece_id,
        clause_id=piece_id,
        text=f"text for {piece_id}",
        source_file="fixture.md",
        country=country,
        doc_type="policy",
        jurisdiction_scope=jurisdiction_scope,
        normative=True,
        temporal_applicability="POINT_IN_TIME",
        effective_date=effective_date,
        effective_date_unresolved=effective_date_unresolved,
        lineage_id=lineage_id,
        supersedes=None,
        superseded_by=None,
    )


# --- T-3.2 hard filters ------------------------------------------------


def test_country_filter_excludes_other_countries_but_keeps_global():
    units = [_unit("in1", country="India"), _unit("ae1", country="UAE"), _unit("g1", country="GLOBAL")]
    kept = filter_by_country(units, "India")
    assert {u.piece_id for u in kept} == {"in1", "g1"}


def test_country_filter_none_is_a_noop():
    units = [_unit("in1", country="India"), _unit("ae1", country="UAE")]
    assert filter_by_country(units, None) == units


def test_jurisdiction_scope_filter_separates_uae_mainland_from_difc():
    units = [
        _unit("mainland1", country="UAE", jurisdiction_scope="uae-mainland"),
        _unit("difc1", country="UAE", jurisdiction_scope="uae-difc"),
        _unit("in1", country="India", jurisdiction_scope=None),  # unscoped, always kept
    ]
    kept = filter_by_jurisdiction_scope(units, "uae-difc")
    assert {u.piece_id for u in kept} == {"difc1", "in1"}


def test_apply_hard_filters_composes_country_then_scope():
    units = [
        _unit("mainland1", country="UAE", jurisdiction_scope="uae-mainland"),
        _unit("difc1", country="UAE", jurisdiction_scope="uae-difc"),
        _unit("in1", country="India"),
    ]
    kept = apply_hard_filters(units, country="UAE", jurisdiction_scope="uae-difc")
    assert {u.piece_id for u in kept} == {"difc1"}


# --- T-3.3 as-of-date resolution ---------------------------------------


def test_as_of_date_picks_the_version_in_force_not_the_newest():
    # P-05 shape: a future-dated amendment must not win just for being newest.
    old = _unit("old", lineage_id="LIN-1", effective_date=dt.date(2020, 1, 1))
    new = _unit("new", lineage_id="LIN-1", effective_date=dt.date(2026, 12, 1))
    kept = select_current_as_of([old, new], as_of_date=dt.date(2026, 9, 3))
    assert [u.piece_id for u in kept] == ["old"]


def test_as_of_date_can_reach_into_the_past():
    old = _unit("old", lineage_id="LIN-1", effective_date=dt.date(2015, 1, 1))
    new = _unit("new", lineage_id="LIN-1", effective_date=dt.date(2018, 3, 29))
    kept = select_current_as_of([old, new], as_of_date=dt.date(2016, 1, 1))
    assert [u.piece_id for u in kept] == ["old"]


def test_lineage_with_no_version_yet_in_force_is_dropped():
    future_only = _unit("future", lineage_id="LIN-2", effective_date=dt.date(2030, 1, 1))
    kept = select_current_as_of([future_only], as_of_date=dt.date(2026, 9, 3))
    assert kept == []


def test_units_without_lineage_pass_through_unchanged():
    standalone = _unit("solo", lineage_id=None, effective_date=dt.date(2020, 1, 1))
    kept = select_current_as_of([standalone], as_of_date=dt.date(2026, 9, 3))
    assert kept == [standalone]


def test_deliberately_unresolved_effective_date_survives_the_filter():
    # R-09 pattern: must not be dropped or defaulted.
    unresolved = _unit("r09", lineage_id="LIN-3", effective_date=None, effective_date_unresolved=True)
    kept = select_current_as_of([unresolved], as_of_date=dt.date(2026, 9, 3))
    assert kept == [unresolved]


# --- T-3.4 lineage dedup (FM-D6) ----------------------------------------


def test_dedup_keeps_only_the_highest_ranked_piece_per_lineage():
    v1 = _unit("v1", lineage_id="LIN-1")
    v2 = _unit("v2", lineage_id="LIN-1")
    other = _unit("other", lineage_id="LIN-2")
    units_by_id = {u.piece_id: u for u in [v1, v2, other]}
    deduped = dedup_by_lineage(["v1", "v2", "other"], units_by_id)
    assert deduped == ["v1", "other"]


def test_dedup_never_collapses_pieces_without_a_lineage_id():
    a = _unit("a", lineage_id=None)
    b = _unit("b", lineage_id=None)
    units_by_id = {u.piece_id: u for u in [a, b]}
    assert dedup_by_lineage(["a", "b"], units_by_id) == ["a", "b"]
