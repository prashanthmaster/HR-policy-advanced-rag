"""
T-6.3 smoke test / manual check -- polls Drive and reports what changed,
without touching sync_state.json (safe to run repeatedly; use --commit to
also mark everything found as seen, e.g. to establish the first baseline
after T-6.2's upload without treating all 8 as "changed").

Run BY HAND in a real terminal (real network, same constraint as every
other Drive/API script in this project):

    .venv-win\\Scripts\\python.exe scripts\\check_for_drive_changes.py
    .venv-win\\Scripts\\python.exe scripts\\check_for_drive_changes.py --commit
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from drive_sync.auth import get_drive_service
from drive_sync.change_detector import detect_changes, mark_seen


def main():
    commit = "--commit" in sys.argv
    service = get_drive_service()
    changes = detect_changes(service)

    if not changes:
        print("No changes detected -- every file matches its last-seen state.")
        return

    print(f"{len(changes)} file(s) changed since last check:")
    for c in changes:
        status = "NEW (never seen before)" if c.old_modified_time is None else "MODIFIED"
        print(f"  [{status}] {c.drive_doc_name}  ({c.rel_path})")
        print(f"      old modifiedTime: {c.old_modified_time}")
        print(f"      new modifiedTime: {c.new_modified_time}")

    if commit:
        for c in changes:
            mark_seen(c)
        print(f"\n--commit passed: marked all {len(changes)} as seen (sync_state.json updated).")
    else:
        print("\n(Dry run -- sync_state.json not touched. Pass --commit to record these as seen.)")


if __name__ == "__main__":
    main()
