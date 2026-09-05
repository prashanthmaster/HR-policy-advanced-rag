#!/usr/bin/env python3
"""
Builds/regenerates eval/baseline/regression_baseline.json from the three
real result files (build/ragas_eval_result.json,
build/citation_accuracy_result.json, build/confusion_matrix_result.json)
that eval/run_ragas_eval.py, eval/run_citation_accuracy_eval.py and
eval/run_confusion_matrix.py just wrote.

This is the ONLY sanctioned way to change the recorded baseline that T-7.2's
scripts/check_regression.py gates future CI runs against -- run this by
hand, deliberately, only after a real reviewed improvement or an
intentional scope change, then commit the updated
eval/baseline/regression_baseline.json alongside the code change that
caused the shift. Never hand-edit the numbers in that file directly.

Usage (from a real terminal, after running all three eval scripts fresh):
    .venv-win\\Scripts\\python.exe scripts\\build_regression_baseline.py
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAGAS_PATH = REPO_ROOT / "build" / "ragas_eval_result.json"
CITATION_PATH = REPO_ROOT / "build" / "citation_accuracy_result.json"
CONFUSION_PATH = REPO_ROOT / "build" / "confusion_matrix_result.json"
OUT_PATH = REPO_ROOT / "eval" / "baseline" / "regression_baseline.json"


def _load(path: Path) -> dict:
    if not path.exists():
        print(f"Missing {path} -- run the three eval scripts first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ragas = _load(RAGAS_PATH)
    citation = _load(CITATION_PATH)
    confusion = _load(CONFUSION_PATH)

    today = _dt.date.today().isoformat()

    baseline = {
        "_comment": (
            "T-7.2's recorded regression baseline -- the real scorecard from a real "
            f"run against the corpus as it stood on {today}. Future CI runs compare "
            "their own real numbers against THIS file and fail the build if any of "
            "them get worse -- never against an invented absolute target. This file "
            "is committed to git so it always travels with the exact code version it "
            "describes. To deliberately accept a new floor (after a real, reviewed "
            "improvement or an intentional scope change), re-run the three eval "
            "scripts and regenerate this file with scripts/build_regression_baseline.py "
            "-- never hand-edit the numbers."
        ),
        "recorded_date": today,
        "judge_model": ragas.get("judge_model"),
        "embedding_model": ragas.get("embedding_model"),
        "total_item_count": ragas.get("total_item_count"),
        "ragas": {
            "scored_item_count": ragas["scored_item_count"],
            **ragas["ragas_means"],
        },
        "citation_accuracy": {
            "scored_item_count": citation["scored_item_count"],
            "mean_citation_accuracy": citation["mean_citation_accuracy"],
            "items_missing_expected_citation": citation["items_missing_expected_citation"],
            "items_with_extra_citation": citation["items_with_extra_citation"],
        },
        "confusion_matrix": {
            "class_match_count": confusion["class_match_count"],
            "over_refusal_count": confusion["over_refusal_count"],
            "over_refusal_probe_ids": confusion["over_refusal_probe_ids"],
            "narrative_only_no_substance_count": confusion["narrative_only_no_substance_count"],
            "answered_count": confusion["answered_count"],
        },
    }

    OUT_PATH.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote new baseline to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
