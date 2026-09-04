"""
Google Drive OAuth authentication -- Slot 4 Phase 6 (freshness sync).

Uses an OAuth "Desktop app" client, not a service account: Google's
"secure by default" org policy (iam.disableServiceAccountKeyCreation) blocks
service-account key downloads on individual/no-organization GCP projects
created after ~2024 -- hit for real on this project, see PROJECT_PLAN.md
Phase 6 Change Log, Session 10. This authenticates as Prashanth's own
Google account instead, via a one-time browser consent flow; after that,
a cached refresh token (GOOGLE_TOKEN_PATH) is reused with no further
browser interaction.

Run scripts/drive_auth_setup.py once, BY HAND, in a real terminal on
Prashanth's own machine -- not through the device-bridge/sandbox shell --
because it opens a real browser window for the login/consent step, which
a sandboxed shell can't display. Same real-network/real-terminal
constraint as the OpenAI/HuggingFace calls in Phases 2-5 (see
slot4_plan_and_conventions.md).
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

# Read-only is all this project ever needs: we only detect and pull changes,
# never write back to Drive.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_credentials() -> Credentials:
    """Return valid OAuth credentials, running the interactive consent flow
    only the first time (or after a revoke) -- otherwise reuse/refresh the
    cached token silently."""
    client_secret_path = os.environ["GOOGLE_CLIENT_SECRET_PATH"]
    token_path = Path(os.environ.get("GOOGLE_TOKEN_PATH", "drive_sync/token.json"))

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return creds


def get_drive_service():
    """Build an authenticated Drive v3 API client."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    return build("drive", "v3", credentials=creds)
