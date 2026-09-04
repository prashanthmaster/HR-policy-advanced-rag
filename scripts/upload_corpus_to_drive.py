"""
T-6.2 -- upload the 9 corpus markdown files to Drive as native Google Docs,
so they become the "live" source of record Prashanth edits for the Phase 6
freshness demo (T-6.7: edit a clause in Drive -> pipeline picks it up).

Uploaded as native Google Docs (mimeType application/vnd.google-apps.document)
rather than plain files, specifically so they're editable directly in the
Drive/Docs browser UI -- the whole point of the live demo. Google's importer
treats the markdown source as plain text, not rendered markdown, so `**bold**`/
`#` headers will show as literal characters in the resulting Doc -- cosmetic
only, the clause text and structure are what matter for this project.

Idempotent: running this twice does NOT create duplicates -- it looks up each
target name in the Drive folder first and skips (reporting) anything already
there. To re-upload a specific file from scratch, delete its Doc in Drive
first.

Writes drive_sync/corpus_manifest.json: {local relative path -> {drive_file_id,
drive_doc_name}}. T-6.3 (change detection) and T-6.4 (incremental re-index)
need this mapping to know which repo corpus file a given Drive edit
corresponds to.

Run BY HAND in a real terminal on Prashanth's machine (not through the
device-bridge shell) -- real network to the Drive API, same constraint as
scripts/drive_auth_setup.py and every other real external-API script in this
project (see slot4_plan_and_conventions.md):

    .venv-win\\Scripts\\python.exe scripts\\upload_corpus_to_drive.py
"""
import io
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseUpload

from drive_sync.auth import get_drive_service

load_dotenv()

CORPUS_ROOT = REPO_ROOT / "corpus"
MANIFEST_PATH = REPO_ROOT / "drive_sync" / "corpus_manifest.json"

# (relative path under corpus/, Drive doc display name)
CORPUS_FILES = [
    ("tier1_law/india/india_law.md", "Tier 1 — India Law"),
    ("tier1_law/uae/uae_law.md", "Tier 1 — UAE Law"),
    ("tier1_law/uae/uae_difc_law.md", "Tier 1 — UAE DIFC Law"),
    ("tier1_law/germany/germany_law.md", "Tier 1 — Germany Law"),
    ("tier2_policy/meridian_global_preamble.md", "Tier 2 — Meridian Global Preamble"),
    ("tier2_policy/india/meridian_india_policy.md", "Tier 2 — Meridian India Policy"),
    ("tier2_policy/uae/meridian_uae_policy.md", "Tier 2 — Meridian UAE Policy"),
    ("tier2_policy/germany/meridian_germany_policy.md", "Tier 2 — Meridian Germany Policy"),
]


def find_existing(service, folder_id, name):
    """Return the Drive file id of `name` in `folder_id` if it already
    exists there, else None. Keeps the script idempotent."""
    safe_name = name.replace("'", "\\'")
    query = (
        f"'{folder_id}' in parents and trashed = false "
        f"and name = '{safe_name}'"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def main():
    folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
    service = get_drive_service()

    manifest = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for rel_path, doc_name in CORPUS_FILES:
        local_path = CORPUS_ROOT / rel_path
        if not local_path.exists():
            print(f"SKIP (missing locally): {rel_path}")
            continue

        existing_id = find_existing(service, folder_id, doc_name)
        if existing_id:
            print(f"SKIP (already in Drive): {doc_name}  (id {existing_id})")
            manifest[rel_path] = {"drive_file_id": existing_id, "drive_doc_name": doc_name}
            continue

        text = local_path.read_text(encoding="utf-8")
        media = MediaIoBaseUpload(
            io.BytesIO(text.encode("utf-8")), mimetype="text/plain", resumable=False
        )
        file_metadata = {
            "name": doc_name,
            "parents": [folder_id],
            "mimeType": "application/vnd.google-apps.document",
        }
        created = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
            .execute()
        )
        print(f"UPLOADED: {doc_name}  (id {created['id']})  {created.get('webViewLink', '')}")
        manifest[rel_path] = {"drive_file_id": created["id"], "drive_doc_name": doc_name}

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifest written: {MANIFEST_PATH.relative_to(REPO_ROOT)} ({len(manifest)} entries)")


if __name__ == "__main__":
    main()
