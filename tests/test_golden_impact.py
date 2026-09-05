"""T-6.9 -- golden-set impact flagging: does a changed clause_id get
correctly matched against the golden probes that depend on it? Pure
in-memory fixtures throughout -- no real golden set file, no API calls."""

from drive_sync.golden_impact import AffectedProbe, find_affected_probes

_FAKE_GOLDEN_ITEMS = [
    {
        "probe_id": "P-03",
        "query": "Dubai. 7 years service. How is my end of service calculated?",
        "expected_clause_ids": ["UAE-DL33-ART51-GRATUITY-FORMULA", "UAE-DL33-ART51-CEILING"],
    },
    {
        "probe_id": "P-3b",
        "query": "How much annual leave do I get? I'm in Dubai.",
        "expected_clause_ids": ["DIFC-L2-2019-LEAVE", "UAE-DL33-ART29-LEAVE", "MER-AE-DIFC-LEAVE"],
    },
    {
        "probe_id": "P-01",
        "query": "I joined 1 Jan 2014 ... What gratuity do I get?",
        "expected_clause_ids": ["IN-GRAT-S4-ELIG", "IN-GRAT-S4-FORMULA", "IN-GRAT-S4-CEILING"],
    },
    {
        "probe_id": "P-21",
        "query": "What's my gratuity?",
        "expected_clause_ids": [],
    },
    {
        "probe_id": "P-39",
        "query": "What's the paternity leave entitlement?",
    },
]


def test_no_match_returns_empty_list():
    assert find_affected_probes({"SOME-UNRELATED-CLAUSE"}, _FAKE_GOLDEN_ITEMS) == []


def test_single_changed_clause_matches_one_probe():
    affected = find_affected_probes({"UAE-DL33-ART51-GRATUITY-FORMULA"}, _FAKE_GOLDEN_ITEMS)
    assert affected == [
        AffectedProbe(
            probe_id="P-03",
            query="Dubai. 7 years service. How is my end of service calculated?",
            matched_clause_ids=("UAE-DL33-ART51-GRATUITY-FORMULA",),
        )
    ]


def test_changed_clause_shared_by_multiple_probes_flags_all_of_them():
    affected = find_affected_probes({"UAE-DL33-ART29-LEAVE"}, _FAKE_GOLDEN_ITEMS)
    assert [a.probe_id for a in affected] == ["P-3b"]


def test_multiple_changed_clauses_across_different_probes():
    affected = find_affected_probes(
        {"UAE-DL33-ART29-LEAVE", "IN-GRAT-S4-ELIG"}, _FAKE_GOLDEN_ITEMS
    )
    assert {a.probe_id for a in affected} == {"P-3b", "P-01"}


def test_probe_with_multiple_matched_clauses_lists_all_matches_sorted():
    affected = find_affected_probes(
        {"UAE-DL33-ART51-GRATUITY-FORMULA", "UAE-DL33-ART51-CEILING"}, _FAKE_GOLDEN_ITEMS
    )
    assert len(affected) == 1
    assert affected[0].matched_clause_ids == (
        "UAE-DL33-ART51-CEILING",
        "UAE-DL33-ART51-GRATUITY-FORMULA",
    )


def test_probes_with_no_expected_clause_ids_never_match_anything():
    # P-21 has an empty list, P-39 has no key at all -- neither should ever
    # be flagged, however many clause_ids changed.
    affected = find_affected_probes(
        {"UAE-DL33-ART51-GRATUITY-FORMULA", "IN-GRAT-S4-ELIG", "UAE-DL33-ART29-LEAVE"},
        _FAKE_GOLDEN_ITEMS,
    )
    assert "P-21" not in {a.probe_id for a in affected}
    assert "P-39" not in {a.probe_id for a in affected}


def test_load_golden_items_reads_real_golden_set_and_has_expected_shape(tmp_path):
    from drive_sync.golden_impact import load_golden_items

    items = load_golden_items()
    assert len(items) == 24
    assert all("probe_id" in it for it in items)
