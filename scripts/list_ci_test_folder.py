"""
One-off helper: lists the files inside the new CI test fixture folder so we
can record their real Drive file IDs, the same way corpus_manifest.json
records IDs for the real 8 corpus documents. Run once by hand after
creating the "CI Test Clause" doc inside that folder.

Usage:
    .venv-win\\Scripts\\python.exe scripts\\list_ci_test_folder.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from drive_sync.auth import get_drive_service

load_dotenv()

CI_TEST_FOLDER_ID = "1piYQmCDGY4cJ5v5_J1RxhKY3draVmwsV"


def main() -> int:
    service = get_drive_service()
    results = (
        service.files()
        .list(
            q=f"'{CI_TEST_FOLDER_ID}' in parents and trashed = false",
            fields="files(id, name, mimeType, modifiedTime)",
        )
        .execute()
    )
    files = results.get("files", [])
    if not files:
        print("No files found in the CI test folder yet -- create the test doc first.")
        return 1

    print(f"{len(files)} file(s) found in the CI test fixture folder:")
    for f in files:
        print(f"  name={f['name']!r}  id={f['id']}  type={f['mimeType']}  modified={f['modifiedTime']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
