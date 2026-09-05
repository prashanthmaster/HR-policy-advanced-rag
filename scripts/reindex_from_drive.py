"""
T-6.4 -- the real freshness sync step: poll Drive, re-index whatever changed.

This is what T-6.7's live demo actually runs. For each file
change_detector.detect_changes() reports, it calls
drive_sync.reindex.reindex_changed_file() -- which pulls the live text,
overwrites the local corpus file, and incrementally updates only that
document's points in the persisted vector index (see drive_sync/reindex.py
for why BM25 needs no separate step here).

A file that fails to re-index is reported and left NOT marked as seen, so
the next run picks it up again rather than silently losing the change.

Run BY HAND in a real terminal (real network -- Drive API + OpenAI API,
same constraint as every other real-API script in this project):

    .venv-win\\Scripts\\python.exe scripts\\reindex_from_drive.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from drive_sync.auth import get_drive_service
from drive_sync.change_detector import detect_changes
from drive_sync.golden_impact import find_affected_probes, load_golden_items
from drive_sync.reindex import reindex_changed_file

load_dotenv()


def main() -> int:
    service = get_drive_service()
    changes = detect_changes(service)

    if not changes:
        print("No changes detected -- index is already current.")
        return 0

    print(f"{len(changes)} file(s) changed -- re-indexing:")
    failures = 0
    all_review_events = []
    for c in changes:
        try:
            result = reindex_changed_file(c, service)
            print(f"  OK: {c.drive_doc_name}  ({c.rel_path}) -- {result.unit_count} unit(s) re-indexed")
            for ev in result.version_events:
                flag = "NEEDS REVIEW" if ev.needs_human_review else "info"
                print(f"      [{flag}] clause {ev.clause_id}: {ev.kind.value}")
                if ev.needs_human_review:
                    all_review_events.append((c, ev))
        except Exception as e:  # noqa: BLE001 -- report and continue with the rest
            failures += 1
            print(f"  FAILED: {c.drive_doc_name}  ({c.rel_path}) -- {e!r}")
            print(f"          Not marked as seen -- will be retried on the next run.")

    if failures:
        print(f"\n{failures}/{len(changes)} file(s) failed to re-index -- see above.")
        return 1

    print(f"\nAll {len(changes)} file(s) re-indexed successfully.")

    if all_review_events:
        print(
            f"\n{len(all_review_events)} clause change(s) need human review before their "
            f"version metadata (effective_date, supersedes/superseded_by) can be trusted -- "
            f"the live text is already updated and searchable either way:"
        )
        for c, ev in all_review_events:
            print(f"\n  {c.drive_doc_name} -- clause {ev.clause_id} ({ev.kind.value})")
            print(f"  {ev.note}")

        # T-6.9 -- the other half of "flag, don't fix": a changed clause can
        # also make a golden probe's recorded golden_answer stale, and that
        # never shows up here on its own (this script never reads the golden
        # set otherwise). Cross-check the changed clause_ids against every
        # probe's expected_clause_ids and flag any overlap -- pure, free,
        # no API calls.
        changed_clause_ids = {ev.clause_id for _, ev in all_review_events}
        try:
            golden_items = load_golden_items()
            affected_probes = find_affected_probes(changed_clause_ids, golden_items)
        except FileNotFoundError:
            affected_probes = []

        if affected_probes:
            print(
                f"\n{len(affected_probes)} golden probe(s) cite a clause that just changed -- "
                f"their recorded golden_answer may now be stale. Re-check before trusting a "
                f"RAGAS Answer Correctness or Citation Accuracy run against them:"
            )
            for probe in affected_probes:
                print(f"\n  {probe.probe_id}: {probe.query}")
                print(f"    changed clause(s): {', '.join(probe.matched_clause_ids)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
