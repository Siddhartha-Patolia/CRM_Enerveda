import base64
import logging
import mimetypes
import os
from email.message import EmailMessage
from email.utils import formataddr
from typing import List

from googleapiclient.discovery import build

import config
from brochure_catalog import Brochure
from google_auth import get_gmail_credentials

logger = logging.getLogger(__name__)

# Workspace caps a message at 25MB, and base64 inflates raw bytes by ~33%, so cap the raw
# attachment total well under that rather than let an oversized send fail slowly.
_MAX_TOTAL_ATTACHMENT_BYTES = 15 * 1024 * 1024

_SUBJECT = "Let's build BESS projects for India! 🇮🇳"


def _build_message(contact: dict, brochures: List[Brochure], sender_name: str) -> EmailMessage:
    body = config.INTRO_MESSAGE_TEMPLATE.format(
        representative_name=contact.get("name") or "there",
        sender_name=sender_name or "",
    )

    message = EmailMessage()
    message["To"] = contact["email"]
    message["From"] = formataddr((config.SENDER_NAME, config.SENDER_EMAIL))
    message["Subject"] = _SUBJECT
    if config.EMAIL_CC:
        message["Cc"] = ", ".join(config.EMAIL_CC)
    # Gmail delivers to Bcc recipients and strips the header before it reaches anyone.
    if config.EMAIL_BCC:
        message["Bcc"] = ", ".join(config.EMAIL_BCC)
    if config.REPLY_TO_EMAIL:
        message["Reply-To"] = config.REPLY_TO_EMAIL
    message.set_content(body)

    for brochure in brochures:
        content_type, _ = mimetypes.guess_type(brochure.path)
        maintype, subtype = (content_type or "application/octet-stream").split("/", 1)
        with open(brochure.path, "rb") as f:
            message.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=f"{brochure.label}.pdf")

    return message


def exceeds_size_limit(brochures: List[Brochure]) -> bool:
    return sum(os.path.getsize(b.path) for b in brochures) > _MAX_TOTAL_ATTACHMENT_BYTES


def send(contact: dict, brochures: List[Brochure], sender_name: str = None) -> bool:
    if exceeds_size_limit(brochures):
        logger.error("Selected brochures are over the email size limit — skipping send.")
        return False

    try:
        service = build("gmail", "v1", credentials=get_gmail_credentials(), cache_discovery=False)
        raw = base64.urlsafe_b64encode(_build_message(contact, brochures, sender_name).as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception:
        logger.exception("Failed to send email via Gmail API")
        return False
