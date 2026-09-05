#!/usr/bin/env python3
"""
T-7.2 -- the actual CI gate. Reads this run's three real result files
(build/ragas_eval_result.json, build/citation_accuracy_result.json,
build/confusion_matrix_result.json) and compares them against the recorded
floor in eval/baseline/regression_baseline.json. Exits non-zero (fails the
build) if any metric got WORSE than the baseline by more than a small
tolerance -- never against an invented absolute number. This is the
project's standing convention (see PROJECT_PLAN.md Phase 7 note): the bar
is "no worse than the last real recorded run," not a made-up target score.

A tolerance (TOLERANCE_SCORE) is allowed on the 0-1 judge-scored metrics
(Context Precision/Recall, Faithfulness, Answer Correctness, Citation
Accuracy) because they depend on an LLM-as-judge call (gpt-4o-mini) that
is not perfectly deterministic between runs, and because GitHub Actions
never caches embeddings between runs (unlike a local machine), so the
retrieved context -- and even which golden items reach ANSWERED at all --
can shift slightly run to run. This was measured for real, not guessed:
two back-to-back local runs landed within ~0.002 of each other, which is
what the original 0.03 tolerance was based on, but two back-to-back real
GitHub Actions runs on IDENTICAL code and corpus swung by up to ~0.045 on
Context Recall/Faithfulness/Answer Correctness (2026-09-05, runs
33952012673 and 33952877889). 0.08 is that observed spread plus a safety
margin -- widened deliberately from evidence, not to paper over a real
regression. The confusion-matrix counts (class match count, over-refusal
count, narrative-only-no-substance count) and the citation-accuracy
problem counts have stayed bit-identical across every real run so far,
including both CI runs, so those stay at an exact no-regression bar
(zero tolerance) -- they are also this project's primary "does it make
the right decision" metric, so that's deliberate, not an oversight.

Usage:
    python scripts/check_regression.py
Exit code 0 = no regression (or an improvement). Exit code 1 = at least
one metric got worse than baseline beyond tolerance -- prints exactly
which metric(s) and by how much.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "eval" / "baseline" / "regression_baseline.json"
RAGAS_PATH = REPO_ROOT / "build" / "ragas_eval_result.json"
CITATION_PATH = REPO_ROOT / "build" / "citation_accuracy_result.json"
CONFUSION_PATH = REPO_ROOT / "build" / "confusion_matrix_result.json"

# Allowed downward wiggle on 0-1 judge-scored metrics, to absorb LLM-judge
# noise between runs -- NOT a lowering of the bar, just a noise floor.
TOLERANCE_SCORE = 0.08


def _load(path: Path) -> dict:
    if not path.exists():
        print(f"FAIL: expected result file missing: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def _check_higher_is_better(label: str, baseline: float, current: float, tolerance: float, failures: list[str]) -> None:
    if current < baseline - tolerance:
        failures.append(
            f"{label}: {current:.4f} is worse than baseline {baseline:.4f} "
            f"(allowed tolerance {tolerance:.4f})"
        )


def _check_lower_is_better(label: str, baseline: float, current: float, tolerance: float, failures: list[str]) -> None:
    if current > baseline + tolerance:
        failures.append(
            f"{label}: {current} is worse than baseline {baseline} "
            f"(allowed tolerance {tolerance})"
        )


def main() -> int:
    baseline = _load(BASELINE_PATH)
    ragas = _load(RAGAS_PATH)
    citation = _load(CITATION_PATH)
    confusion = _load(CONFUSION_PATH)

    failures: list[str] = []

    # --- RAGAS metrics: higher is better, small tolerance for judge noise ---
    b_ragas = baseline["ragas"]
    r_ragas = ragas["ragas_means"]
    for key in ("mean_context_precision", "mean_context_recall", "mean_faithfulness", "mean_answer_correctness"):
        _check_higher_is_better(f"ragas.{key}", b_ragas[key], r_ragas[key], TOLERANCE_SCORE, failures)

    # --- Citation accuracy: mean is higher-is-better; the two problem
    # counts are lower-is-better (fewer missing/extra citations) ---
    b_cite = baseline["citation_accuracy"]
    _check_higher_is_better(
        "citation_accuracy.mean_citation_accuracy",
        b_cite["mean_citation_accuracy"], citation["mean_citation_accuracy"],
        TOLERANCE_SCORE, failures,
    )
    _check_lower_is_better(
        "citation_accuracy.items_missing_expected_citation",
        b_cite["items_missing_expected_citation"], citation["items_missing_expected_citation"],
        0, failures,
    )
    _check_lower_is_better(
        "citation_accuracy.items_with_extra_citation",
        b_cite["items_with_extra_citation"], citation["items_with_extra_citation"],
        0, failures,
    )

    # --- Confusion matrix: plain classification counts, zero tolerance ---
    b_conf = baseline["confusion_matrix"]
    _check_higher_is_better(
        "confusion_matrix.class_match_count",
        b_conf["class_match_count"], confusion["class_match_count"], 0, failures,
    )
    _check_lower_is_better(
        "confusion_matrix.over_refusal_count",
        b_conf["over_refusal_count"], confusion["over_refusal_count"], 0, failures,
    )
    _check_lower_is_better(
        "confusion_matrix.narrative_only_no_substance_count",
        b_conf["narrative_only_no_substance_count"], confusion["narrative_only_no_substance_count"], 0, failures,
    )

    print(f"Comparing this run's real numbers against the baseline recorded {baseline['recorded_date']}...")
    if failures:
        print(f"\nREGRESSION DETECTED -- {len(failures)} metric(s) got worse than the recorded baseline:\n")
        for f in failures:
            print(f"  - {f}")
        print(
            "\nIf this is a deliberate, reviewed change (not a bug), re-run the three "
            "eval scripts and regenerate eval/baseline/regression_baseline.json to "
            "accept the new floor -- never hand-edit the numbers."
        )
        return 1

    print("No regression -- every metric is at or above the recorded baseline (within tolerance).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
