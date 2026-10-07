"""Minimal WhatsApp Cloud API webhook, plus the "Chat with us" redirect.

Meta requires a verified callback URL for production setup. We don't act on any incoming
events (replies are handled manually in the WhatsApp Business app), so this only answers
the verification handshake and acknowledges every event with 200.

Meta doesn't allow wa.me links in template buttons, so the outreach template's
"Chat with us" button points at /chat here, which redirects to the Business app number.
"""
import logging
import os

from flask import Flask, redirect, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("webhook")

VERIFY_TOKEN = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
CHAT_REDIRECT_URL = os.environ.get("CHAT_REDIRECT_URL", "https://wa.me/919510669707")


@app.get("/webhook")
def verify():
    if (
        VERIFY_TOKEN
        and request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return request.args.get("hub.challenge", ""), 200
    return "Forbidden", 403


@app.post("/webhook")
def receive():
    # Nothing is stored; delivery statuses are only logged so failed sends can be diagnosed
    # from the host's logs (the send API returning 200 doesn't mean the message was delivered).
    try:
        for entry in (request.get_json(silent=True) or {}).get("entry", []):
            for change in entry.get("changes", []):
                for status in change.get("value", {}).get("statuses", []):
                    logger.info(
                        "WhatsApp status: %s to %s (message %s) errors=%s",
                        status.get("status"),
                        status.get("recipient_id"),
                        status.get("id"),
                        status.get("errors"),
                    )
    except Exception:
        logger.exception("Failed to read webhook payload")
    return "", 200


@app.get("/chat")
def chat():
    # 302, not 301, so browsers don't cache it and the target can be changed later.
    return redirect(CHAT_REDIRECT_URL, code=302)


@app.get("/")
def health():
    return "ok", 200
