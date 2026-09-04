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
    for c in changes:
        try:
            unit_count = reindex_changed_file(c, service)
            print(f"  OK: {c.drive_doc_name}  ({c.rel_path}) -- {unit_count} unit(s) re-indexed")
        except Exception as e:  # noqa: BLE001 -- report and continue with the rest
            failures += 1
            print(f"  FAILED: {c.drive_doc_name}  ({c.rel_path}) -- {e!r}")
            print(f"          Not marked as seen -- will be retried on the next run.")

    if failures:
        print(f"\n{failures}/{len(changes)} file(s) failed to re-index -- see above.")
        return 1

    print(f"\nAll {len(changes)} file(s) re-indexed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
