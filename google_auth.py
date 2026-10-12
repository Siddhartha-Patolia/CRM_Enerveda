import json
import os

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

import config

_SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_sheets_credentials() -> service_account.Credentials:
    """crm-sheets service account: Editor on the outreach sheet (shared with its email).

    On servers the key's contents come from SHEETS_SERVICE_ACCOUNT_JSON (secrets/ isn't
    deployed); locally the key file in secrets/ is used.
    """
    if config.SHEETS_SERVICE_ACCOUNT_JSON:
        info = json.loads(config.SHEETS_SERVICE_ACCOUNT_JSON)
        return service_account.Credentials.from_service_account_info(info, scopes=_SHEETS_SCOPES)
    if os.path.exists(config.SHEETS_SERVICE_ACCOUNT_FILE):
        return service_account.Credentials.from_service_account_file(
            config.SHEETS_SERVICE_ACCOUNT_FILE, scopes=_SHEETS_SCOPES
        )
    raise RuntimeError(
        "No Sheets service account key configured — set SHEETS_SERVICE_ACCOUNT_JSON or add "
        f"{config.SHEETS_SERVICE_ACCOUNT_FILE}."
    )


def get_gmail_credentials() -> Credentials:
    """OAuth token for SENDER_EMAIL, created once with scripts/gmail_login.py.

    Railway blocks outbound SMTP, so mail goes through the Gmail API over HTTPS instead.
    The token refreshes itself; it only needs redoing if the sender revokes access or
    changes their Google password.
    """
    if config.GMAIL_TOKEN_JSON:
        creds = Credentials.from_authorized_user_info(json.loads(config.GMAIL_TOKEN_JSON), GMAIL_SCOPES)
    elif os.path.exists(config.GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN_FILE, GMAIL_SCOPES)
    else:
        raise RuntimeError(
            f"No Gmail token configured — run scripts/gmail_login.py, then set GMAIL_TOKEN_JSON "
            f"or keep {config.GMAIL_TOKEN_FILE}."
        )

    if not creds.valid:
        if not creds.refresh_token:
            raise RuntimeError("Gmail token has no refresh token — run scripts/gmail_login.py again.")
        creds.refresh(Request())
    return creds
