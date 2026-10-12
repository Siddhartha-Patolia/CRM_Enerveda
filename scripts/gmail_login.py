"""One-time Gmail sign-in for the outreach sender (run locally, not on the server).

    ./env/bin/python -m scripts.gmail_login           # remote: sender approves on their own device
    ./env/bin/python -m scripts.gmail_login --local   # sender signs in on this machine's browser

Remote flow: open the printed link on any device, sign in as SENDER_EMAIL, allow access.
The browser then lands on a localhost page that fails to load — copy that full address
and paste it here. Needs the Desktop OAuth client JSON at secrets/oauth_client.json.

Writes the token to GMAIL_TOKEN_FILE; paste that file's contents into GMAIL_TOKEN_JSON on
the server.
"""
import base64
import json
import os
import sys

# The remote flow's redirect is plain http://localhost, and Google may return the granted
# scopes in a different order than requested; neither is a problem for a Desktop client.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from google_auth_oauthlib.flow import Flow, InstalledAppFlow

import config
from google_auth import GMAIL_SCOPES

_CLIENT_FILE = "secrets/oauth_client.json"
# openid/email only let us confirm which account signed in; sending needs gmail.send alone.
_SCOPES = GMAIL_SCOPES + ["openid", "https://www.googleapis.com/auth/userinfo.email"]
_REDIRECT_URI = "http://localhost:8765/"


def _signed_in_email(creds) -> str:
    payload = creds.id_token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["email"]


def main() -> None:
    if not os.path.exists(_CLIENT_FILE):
        sys.exit(f"Missing {_CLIENT_FILE} — download the Desktop OAuth client JSON from Cloud Console.")

    if "--local" in sys.argv:
        flow = InstalledAppFlow.from_client_secrets_file(_CLIENT_FILE, _SCOPES)
        creds = flow.run_local_server(port=0, login_hint=config.SENDER_EMAIL, access_type="offline", prompt="consent")
    else:
        flow = Flow.from_client_secrets_file(_CLIENT_FILE, _SCOPES, redirect_uri=_REDIRECT_URI)
        url, _ = flow.authorization_url(access_type="offline", prompt="consent", login_hint=config.SENDER_EMAIL)
        print(f"\nSend this link to the sender ({config.SENDER_EMAIL}):\n\n{url}\n")
        print("After they allow access, their browser shows a page that won't load.")
        redirected = input("Paste the full address from their address bar here:\n> ").strip()
        flow.fetch_token(authorization_response=redirected)
        creds = flow.credentials

    email = _signed_in_email(creds)
    if email.lower() != config.SENDER_EMAIL.lower():
        sys.exit(f"Signed in as {email}, but SENDER_EMAIL is {config.SENDER_EMAIL} — token not saved.")
    if not creds.refresh_token:
        sys.exit("Google didn't return a refresh token — run this again.")

    os.makedirs(os.path.dirname(config.GMAIL_TOKEN_FILE), exist_ok=True)
    with open(config.GMAIL_TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"\nSaved token for {email} to {config.GMAIL_TOKEN_FILE}.")
    print("On Railway, set GMAIL_TOKEN_JSON to this file's full contents.")


if __name__ == "__main__":
    main()
