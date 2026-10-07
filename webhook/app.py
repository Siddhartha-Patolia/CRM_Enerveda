"""Minimal WhatsApp Cloud API webhook.

Meta requires a verified callback URL for production setup. We don't act on any incoming
events (replies are handled manually in the WhatsApp Business app), so this only answers
the verification handshake and acknowledges every event with 200.
"""
import os

from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")


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
    return "", 200


@app.get("/")
def health():
    return "ok", 200
