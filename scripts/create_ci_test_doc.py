"""
One-off helper: creates the CI test fixture document THROUGH THE APP itself,
inside the CI test folder. This matters because the app's Drive permission
(`drive.file`) only ever lets it see files it created itself (or files a
human explicitly hands it via a picker, which this project doesn't use) --
a document created by hand directly in the Drive website is invisible to
the app no matter what, so the test doc has to be created this way, same
as scripts/upload_corpus_to_drive.py did for the real 8 corpus documents.

Usage:
    .venv-win\\Scripts\\python.exe scripts\\create_ci_test_doc.py
"""
import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseUpload

from drive_sync.auth import get_drive_service

load_dotenv()

CI_TEST_FOLDER_ID = "1piYQmCDGY4cJ5v5_J1RxhKY3draVmwsV"

CONTENT = """clause_id: CI-TEST-FIXTURE-001
country: Testland
doc_type: policy
normative: true
---
This is a fake practice clause used only by the automated testing system. It has no real legal meaning. Employees of Testland are entitled to seven (7) days of imaginary leave per year.
"""


def main() -> int:
    service = get_drive_service()

    media = MediaIoBaseUpload(io.BytesIO(CONTENT.encode("utf-8")), mimetype="text/plain", resumable=False)
    file_metadata = {
        "name": "CI Test Clause (app-created)",
        "parents": [CI_TEST_FOLDER_ID],
        "mimeType": "application/vnd.google-apps.document",
    }
    created = service.files().create(body=file_metadata, media_body=media, fields="id, name").execute()

    print(f"Created: {created['name']!r}  id={created['id']}")
    print("This file is now visible to the app (drive.file scope covers anything the app itself created).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
