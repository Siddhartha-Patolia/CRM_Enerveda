import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")

MODEL = "gemini-3.5-flash-lite"

# Timestamps in the Sheet and token log are in IST, not the host's clock (Railway runs on UTC).
LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30), "IST")

GEMINI_TIMEOUT_SECONDS = 90

OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "")
OAUTH_TOKEN_PATH = os.environ.get("OAUTH_TOKEN_PATH", "secrets/token.json")
# Contents of a token.json from a local login. Set this on servers (e.g. Railway), where
# secrets/ isn't deployed and the browser login flow can't run.
GOOGLE_TOKEN_JSON = os.environ.get("GOOGLE_TOKEN_JSON", "")

GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
]

GOOGLE_SHEETS_ID = os.environ.get("GOOGLE_SHEETS_ID", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")

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

if not OAUTH_CLIENT_ID or not OAUTH_CLIENT_SECRET:
    raise RuntimeError("OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET missing.")

if not GOOGLE_SHEETS_ID:
    raise RuntimeError("GOOGLE_SHEETS_ID missing.")
