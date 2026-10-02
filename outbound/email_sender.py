import base64
import logging
import mimetypes
import os
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from typing import List

from googleapiclient.discovery import build

import config
from brochure_catalog import Brochure
from google_auth import get_credentials

logger = logging.getLogger(__name__)

# Gmail API caps the whole base64-encoded message at ~35MB (36,700,160 bytes). Base64
# inflates raw bytes by ~33%, so cap the raw attachment total well under that threshold
# rather than let an oversized send stall/fail slowly over the network.
_MAX_TOTAL_ATTACHMENT_BYTES = 20 * 1024 * 1024


def _get_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def _build_message(contact: dict, brochures: List[Brochure], sender_name: str) -> MIMEMultipart:
    body = config.INTRO_MESSAGE_TEMPLATE.format(
        representative_name=contact.get("name") or "there",
        sender_name=sender_name or "",
    )

    message = MIMEMultipart()
    message["to"] = contact["email"]
    message["from"] = config.SENDER_EMAIL
    message["subject"] = "Great connecting with you"
    message.attach(MIMEText(body))

    for brochure in brochures:
        content_type, _ = mimetypes.guess_type(brochure.path)
        with open(brochure.path, "rb") as f:
            part = MIMEBase(*(content_type or "application/octet-stream").split("/", 1))
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", "attachment", filename=f"{brochure.label}.pdf"
        )
        message.attach(part)

    return message


def exceeds_size_limit(brochures: List[Brochure]) -> bool:
    return sum(os.path.getsize(b.path) for b in brochures) > _MAX_TOTAL_ATTACHMENT_BYTES


def send(contact: dict, brochures: List[Brochure], sender_name: str = None) -> bool:
    if exceeds_size_limit(brochures):
        logger.error("Selected brochures are over the email size limit — skipping send.")
        return False

    try:
        service = _get_service()
        message = _build_message(contact, brochures, sender_name)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception:
        logger.exception("Failed to send email via Gmail API")
        return False
