import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Comma-separated Telegram user IDs allowed to use the bot (staff). Empty = anyone.
ALLOWED_TELEGRAM_USER_IDS = {
    int(i) for i in os.environ.get("ALLOWED_TELEGRAM_USER_IDS", "").replace(" ", "").split(",") if i
}

GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")

MODEL = "gemini-3.5-flash-lite"

# Timestamps in the Sheet and token log are in IST, not the host's clock (Railway runs on UTC).
LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30), "IST")

GEMINI_TIMEOUT_SECONDS = 90

# Sheets logging uses the crm-sheets service account (no browser login, no expiring token),
# shared as Editor on the sheet. Locally the key file in secrets/ is used; on servers
# (Railway) set SHEETS_SERVICE_ACCOUNT_JSON to the key file's contents.
SHEETS_SERVICE_ACCOUNT_JSON = os.environ.get("SHEETS_SERVICE_ACCOUNT_JSON", "")
SHEETS_SERVICE_ACCOUNT_FILE = os.environ.get("SHEETS_SERVICE_ACCOUNT_FILE", "secrets/sheets_service_account.json")

GOOGLE_SHEETS_ID = os.environ.get("GOOGLE_SHEETS_ID", "")
# Outreach email is sent through the Gmail API (HTTPS — Railway blocks outbound SMTP) as
# this Workspace mailbox, using an OAuth token created once with scripts/gmail_login.py.
# Replies land in its inbox unless REPLY_TO_EMAIL is set. EMAIL_CC / EMAIL_BCC are optional
# comma-separated lists. On servers set GMAIL_TOKEN_JSON to the token file's contents.
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
GMAIL_TOKEN_JSON = os.environ.get("GMAIL_TOKEN_JSON", "")
GMAIL_TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "secrets/gmail_token.json")
SENDER_NAME = os.environ.get("SENDER_NAME", "Enerveda Vault LLP")
REPLY_TO_EMAIL = os.environ.get("REPLY_TO_EMAIL", "")
EMAIL_CC = [e.strip() for e in os.environ.get("EMAIL_CC", "").split(",") if e.strip()]
EMAIL_BCC = [e.strip() for e in os.environ.get("EMAIL_BCC", "").split(",") if e.strip()]

WHATSAPP_PHONE_NO_ID = os.environ.get("WHATSAPP_PHONE_NO_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_API_VERSION = "v23.0"

PROMPT_TEXT = (
    "You are reading a photo of a business card. Extract exactly what is printed on the "
    "card — never infer, guess, autocomplete, or fill in a field from general knowledge, "
    "a logo design, or a domain name. If you are not fully confident in a field, leave it "
    "null rather than guessing.\n\n"
    "- name: the full name of an individual person, only if one is clearly printed as a "
    "person's name (not a company name, slogan, or job title alone). Many cards only list "
    "a company with no individual named — leave null in that case.\n"
    "- company: the company/organization name, only if that exact text is printed on the "
    "card. Do not derive it from a website domain, or an email domain — use it only "
    "if the company name itself appears as text.\n"
    "- phone: the primary phone number exactly as printed, digits and symbols included.\n"
    "- email: the email address, read character by character. Do not confuse it with a "
    "website URL. A valid email has exactly one '@' and a domain after it — if you can't "
    "read every character with confidence, leave it null rather than guessing.\n\n"
    "Leave any field null if it isn't clearly present on the card."
)

INTRO_MESSAGE_TEMPLATE = (
    "Hi {representative_name}\n\n"
    "It was great connecting with you at the REI 2026 at our stall !\n\n"
    "Here is our detailed company brochure with all product information for your kind "
    "reference.\n\n"
    "Looking forward to working together on future projects.\n\n"
    "{sender_name}\n"
    "Enerveda Vault LLP"
)

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Telegram bot token missing")

if not GEMINI_API_KEY:
    raise RuntimeError("Gemini API key missing.")

if not SENDER_EMAIL:
    raise RuntimeError("SENDER_EMAIL missing.")

if not GOOGLE_SHEETS_ID:
    raise RuntimeError("GOOGLE_SHEETS_ID missing.")
