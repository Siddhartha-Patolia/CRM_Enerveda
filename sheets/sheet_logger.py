import datetime
import logging

from googleapiclient.discovery import build

import config
from google_auth import get_credentials

logger = logging.getLogger(__name__)

_SHEET_NAME = "Sheet1"
_HEADER_RANGE = f"{_SHEET_NAME}!A1:I1"
_APPEND_RANGE = f"{_SHEET_NAME}!A:I"
_HEADER = [
    "Company Name",
    "Representative Name",
    "Contact Number",
    "Email",
    "Brochures Sent",
    "Timestamp",
    "Sender Name",
    "Email Outreach",
    "WhatsApp Outreach",
]


def _get_service():
    creds = get_credentials()
    return build("sheets", "v4", credentials=creds)


def _ensure_header(service) -> None:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=config.GOOGLE_SHEETS_ID, range=_HEADER_RANGE)
        .execute()
    )
    values = result.get("values", [])
    if not values or values[0] != _HEADER:
        service.spreadsheets().values().update(
            spreadsheetId=config.GOOGLE_SHEETS_ID,
            range=_HEADER_RANGE,
            valueInputOption="RAW",
            body={"values": [_HEADER]},
        ).execute()


def append_row(
    company: str,
    representative_name: str,
    phone: str,
    email: str,
    brochures_sent: str,
    sender_name: str = None,
    email_outreach: str = None,
    whatsapp_outreach: str = None,
    timestamp: str = None,
) -> bool:
    timestamp = timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        service = _get_service()
        _ensure_header(service)
        service.spreadsheets().values().append(
            spreadsheetId=config.GOOGLE_SHEETS_ID,
            range=_APPEND_RANGE,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={
                "values": [
                    [
                        company or "",
                        representative_name or "",
                        phone or "",
                        email or "",
                        brochures_sent or "",
                        timestamp,
                        sender_name or "",
                        email_outreach or "",
                        whatsapp_outreach or "",
                    ]
                ]
            },
        ).execute()
        return True
    except Exception:
        logger.exception("Failed to append row to Google Sheet")
        return False
