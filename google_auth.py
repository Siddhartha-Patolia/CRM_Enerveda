import json
import os

from google.oauth2 import service_account

import config

_SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


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
