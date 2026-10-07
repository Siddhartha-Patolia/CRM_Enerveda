import logging
import re
from typing import List, Optional

import requests

import config
from brochure_catalog import Brochure

logger = logging.getLogger(__name__)

_PHONE_ID = config.WHATSAPP_PHONE_NO_ID
_MESSAGES_URL = f"https://graph.facebook.com/{config.WHATSAPP_API_VERSION}/{_PHONE_ID}/messages"
_MEDIA_URL = f"https://graph.facebook.com/{config.WHATSAPP_API_VERSION}/{_PHONE_ID}/media"

_TEMPLATE_NAME = "crm_enerveda_util"
_TEMPLATE_LANGUAGE = "en"

# crm_enerveda_util (UTILITY, Enerveda LLP account) is APPROVED. Its "Chat with us" button
# points at chat.enervedavault.com/chat (webhook service), which redirects to the Business app
# number. Body takes only receiver_name. crm_enerveda_v2 is the approved MARKETING fallback
# with the same variables and button.
USE_TEST_TEMPLATE = False


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"}


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def _post_template_message(to: str, template_name: str, language_code: str, components: Optional[list] = None) -> bool:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    if components:
        payload["template"]["components"] = components

    try:
        response = requests.post(_MESSAGES_URL, headers=_auth_headers(), json=payload, timeout=30)
        if not response.ok:
            logger.error("WhatsApp send failed (%s): %s", response.status_code, response.text)
            return False
        return True
    except Exception:
        logger.exception("Failed to send WhatsApp template message")
        return False


def send_hello_world_test(to: str) -> bool:
    """Connectivity test using Meta's pre-approved default template.

    This is NOT the real outreach message — 'hello_world' is a fixed, non-customizable
    template Meta provides out of the box so you can verify credentials/wiring before a
    real template (with our intro text + a document header for brochures) is approved.
    """
    return _post_template_message(to, template_name="hello_world", language_code="en_US")


def _upload_media(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            response = requests.post(
                _MEDIA_URL,
                headers=_auth_headers(),
                data={"messaging_product": "whatsapp", "type": "application/pdf"},
                files={"file": (path, f, "application/pdf")},
                timeout=60,
            )
        response.raise_for_status()
        return response.json().get("id")
    except Exception:
        logger.exception("Failed to upload brochure media to WhatsApp")
        return None


def _send_brochure(to: str, brochure: Brochure, receiver_name: str) -> bool:
    media_id = _upload_media(brochure.path)
    if not media_id:
        return False

    components = [
        {
            "type": "header",
            "parameters": [
                {
                    "type": "document",
                    "document": {"id": media_id, "filename": f"{brochure.label}.pdf"},
                }
            ],
        },
        {
            "type": "body",
            "parameters": [
                {"type": "text", "parameter_name": "receiver_name", "text": receiver_name},
            ],
        },
    ]
    return _post_template_message(to, _TEMPLATE_NAME, _TEMPLATE_LANGUAGE, components)


def send(contact: dict, brochures: List[Brochure], sender_name: str = None) -> bool:
    to = _normalize_phone(contact.get("phone"))
    if not to:
        logger.error("No usable phone number to send WhatsApp message to")
        return False

    if USE_TEST_TEMPLATE:
        return send_hello_world_test(to)

    # sender_name is still accepted (callers pass it) but the template no longer shows it.
    receiver_name = contact.get("name") or "there"

    all_ok = True
    for brochure in brochures:
        ok = _send_brochure(to, brochure, receiver_name)
        if not ok:
            all_ok = False
            logger.error("Failed to send brochure '%s' over WhatsApp", brochure.label)
    return all_ok
