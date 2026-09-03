"""T-2.5 tests: the change-kind classifier."""

from __future__ import annotations

import pytest

from ingestion.change_kind import ChangeKind, classify_change


def test_addition_when_no_prior_text():
    assert classify_change(None, "new clause text") == ChangeKind.ADDITION


def test_sunset_when_text_removed():
    assert classify_change("old clause text", None) == ChangeKind.SUNSET


def test_sunset_when_explicit_withdrawal_added():
    assert classify_change(
        "Employees are entitled to X.",
        "This clause has been withdrawn effective 2026-01-01.",
    ) == ChangeKind.SUNSET


def test_no_op_on_identical_text():
    text = "Notice period is thirty days."
    assert classify_change(text, text) == ChangeKind.NO_OP


def test_editorial_on_whitespace_and_punctuation_only_change():
    old = "Notice period is thirty days, payable in lieu."
    new = "Notice period is thirty days payable in lieu"
    assert classify_change(old, new) == ChangeKind.EDITORIAL


def test_editorial_on_case_only_change():
    old = "the employee must give notice."
    new = "THE EMPLOYEE MUST GIVE NOTICE."
    assert classify_change(old, new) == ChangeKind.EDITORIAL


def test_substantive_on_number_change():
    old = "Notice period is fifteen days."
    new = "Notice period is thirty days."
    assert classify_change(old, new) == ChangeKind.SUBSTANTIVE


def test_both_none_raises():
    with pytest.raises(ValueError):
        classify_change(None, None)
