"""
T-6.3 -- change detection by polling.

Compares each corpus file's live Drive `modifiedTime` against the last
value we saw (drive_sync/sync_state.json). Polling, not Drive's push-
notification API: this project has no public webhook endpoint for Drive to
call, and a poll is simpler to run, demo, and reason about at this scale --
a deliberate scope choice, not an oversight (see PROJECT_PLAN.md Phase 6).

Pure detection only -- this module never writes state on its own. T-6.4 (the
re-indexer) calls mark_seen() only after it has actually re-indexed a
changed file successfully, so a detected-but-not-yet-processed change is
never silently forgotten if re-indexing fails partway through.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "drive_sync" / "corpus_manifest.json"
STATE_PATH = REPO_ROOT / "drive_sync" / "sync_state.json"


@dataclass(frozen=True)
class ChangedFile:
    rel_path: str
    drive_file_id: str
    drive_doc_name: str
    old_modified_time: str | None  # None means "never seen before" (first poll)
    new_modified_time: str


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def detect_changes(service) -> list[ChangedFile]:
    """Poll Drive for every file in corpus_manifest.json; return those whose
    modifiedTime differs from (or is absent from) sync_state.json.

    Does NOT update sync_state.json -- call mark_seen() once each change has
    actually been processed.
    """
    manifest = _load_json(MANIFEST_PATH)
    state = _load_json(STATE_PATH)

    changes = []
    for rel_path, entry in manifest.items():
        file_id = entry["drive_file_id"]
        meta = service.files().get(fileId=file_id, fields="modifiedTime, name").execute()
        new_modified = meta["modifiedTime"]
        old_modified = state.get(file_id, {}).get("modifiedTime")

        if old_modified != new_modified:
            changes.append(
                ChangedFile(
                    rel_path=rel_path,
                    drive_file_id=file_id,
                    drive_doc_name=entry["drive_doc_name"],
                    old_modified_time=old_modified,
                    new_modified_time=new_modified,
                )
            )
    return changes


def mark_seen(changed: ChangedFile) -> None:
    """Record that `changed` has been fully processed (re-indexed), so the
    next poll doesn't report it again."""
    state = _load_json(STATE_PATH)
    state[changed.drive_file_id] = {
        "modifiedTime": changed.new_modified_time,
        "drive_doc_name": changed.drive_doc_name,
        "rel_path": changed.rel_path,
    }
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def export_plain_text(service, drive_file_id: str) -> str:
    """Export a Google Doc's current live content as plain text -- what
    T-6.4 actually re-indexes."""
    content = service.files().export(fileId=drive_file_id, mimeType="text/plain").execute()
    return content.decode("utf-8") if isinstance(content, bytes) else content
