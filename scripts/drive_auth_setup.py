"""
One-time interactive setup + connection test for Phase 6, T-6.1.

Run this yourself, BY HAND, in a real Windows terminal (not through Claude's
device-bridge shell) from the repo root:

    .venv-win\\Scripts\\python.exe scripts\\drive_auth_setup.py

First run: a browser window opens asking you to log into your Google
account and click Allow. After that it saves drive_sync/token.json so this
never asks again -- any future run (this script, or the real sync code
later) just reuses that token silently.

Either way, it then lists what's actually in the configured Drive folder --
that's the proof the whole chain (GCP project -> Drive API enabled -> OAuth
client -> your consent -> folder access) really works end to end.
"""
import os

from dotenv import load_dotenv

from drive_sync.auth import get_drive_service

load_dotenv()


def main():
    folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
    service = get_drive_service()

    results = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType, modifiedTime)",
        )
        .execute()
    )
    files = results.get("files", [])

    print(f"Connected. Folder {folder_id} contains {len(files)} item(s):")
    for f in files:
        print(f"  - {f['name']}  ({f['mimeType']}, modified {f['modifiedTime']})")

    if not files:
        print(
            "\n(Folder is empty -- expected if you haven't uploaded the corpus "
            "yet. This still confirms the connection itself works: project, "
            "Drive API, OAuth client, and your consent are all wired up correctly.)"
        )


if __name__ == "__main__":
    main()
