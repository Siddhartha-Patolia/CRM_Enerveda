import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import config


def get_credentials() -> Credentials:
    creds = None
    if os.path.exists(config.OAUTH_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(config.OAUTH_TOKEN_PATH, config.GOOGLE_OAUTH_SCOPES)
    elif config.GOOGLE_TOKEN_JSON:
        creds = Credentials.from_authorized_user_info(json.loads(config.GOOGLE_TOKEN_JSON), config.GOOGLE_OAUTH_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif config.GOOGLE_TOKEN_JSON:
            # On a server there's no browser to log in with, so fail loudly instead of hanging.
            raise RuntimeError("GOOGLE_TOKEN_JSON is set but unusable — log in locally and copy a fresh token.json.")
        else:
            client_config = {
                "installed": {
                    "client_id": config.OAUTH_CLIENT_ID,
                    "client_secret": config.OAUTH_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, config.GOOGLE_OAUTH_SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(config.OAUTH_TOKEN_PATH), exist_ok=True)
        with open(config.OAUTH_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return creds
