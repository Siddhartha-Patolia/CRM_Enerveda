# CRM Enerveda

A Telegram bot that automates business-card outreach: scan a card, review the extracted
contact details, pick which brochures to send, and the bot emails and WhatsApps them while
logging every outreach event to a Google Sheet.

## How it works

1. Send a photo of a business card to the Telegram bot.
2. Gemini (vision) extracts name, company, phone, and email — never guessing a field it
   isn't confident about.
3. You pick one or more brochures from a checklist (auto-discovered from `brochures/*.pdf`
   — no config file to maintain, just drop PDFs in that folder).
4. A review screen shows everything found, with buttons to manually correct any field
   before sending (OCR misreads happen — this is the safety net).
5. On confirm, the bot emails the intro message + selected brochure(s), sends the same via
   WhatsApp (template message with a document header), and — once at least one channel
   succeeds — logs the whole event to a Google Sheet: company, contact, brochures sent,
   timestamp, sender, and a Sent/Failed status per channel.
6. Gemini token usage (input/output/total) for every card processed is logged locally to
   `token_logs.csv`.

Email and WhatsApp sends run concurrently, not sequentially, to keep the whole flow fast.

## Project structure

```
bot/
  main.py           entrypoint — builds the Telegram Application, registers handlers
  conversation.py   the whole conversation state machine (photo -> review -> confirm)
  keyboards.py      inline keyboard builders (brochure checklist, review screen)
config.py           loads .env, holds the Gemini prompt and the email/WhatsApp intro copy
brochure_catalog.py scans brochures/*.pdf — the filename (minus extension) is both the
                    internal key and the display label
extraction/
  gemini_client.py  sends the card image to Gemini, returns (contact, token usage)
outbound/
  email_sender.py   Gmail SMTP send as SENDER_EMAIL (intro text + brochure attachments)
  whatsapp_sender.py WhatsApp Cloud API send (template message + document media)
sheets/
  sheet_logger.py   appends one row per successful outreach to the Google Sheet
google_auth.py      Google service-account credentials for Sheets
token_logger.py     appends Gemini token usage to token_logs.csv
brochures/          the actual brochure PDFs — whatever's here is what users can pick
secrets/            local service-account key file (gitignored)
webhook/            minimal WhatsApp webhook (deployed separately, e.g. on Render)
```

## Setup

### 1. Install

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### 2. Telegram bot

Message [@BotFather](https://t.me/BotFather) on Telegram, `/newbot`, follow the prompts.
Copy the token into `.env` as `TELEGRAM_BOT_TOKEN`.

### 3. Gemini API key

Get one from [Google AI Studio](https://aistudio.google.com/). Put it in `.env` as
`GOOGLE_GEMINI_API_KEY`.

### 4. Google Sheets (service account)

1. In [Google Cloud Console](https://console.cloud.google.com), enable the **Google Sheets
   API**, then IAM & Admin -> Service Accounts -> create `crm-sheets` (no roles) -> Keys ->
   Add key -> JSON. Save it as `secrets/sheets_service_account.json`.
2. Share the sheet with the key's `client_email` as **Editor** and put the sheet's ID (from
   its URL) into `GOOGLE_SHEETS_ID`.

No browser login and no expiring token.

### 4b. Email (Gmail SMTP with an app password)

1. On the Workspace account the email is sent from, turn on 2-Step Verification, then
   create an app password at myaccount.google.com/apppasswords.
2. Set `SENDER_EMAIL` to that address and `SMTP_APP_PASSWORD` to the app password.
   Optional: `SENDER_NAME`, `REPLY_TO_EMAIL`, `EMAIL_CC`, `EMAIL_BCC`.

Sent mail appears in the account's Sent folder and replies go to its inbox (or
`REPLY_TO_EMAIL`). The app password stops working if the account's Google password changes.

### 5. WhatsApp (Meta Cloud API)

1. [developers.facebook.com](https://developers.facebook.com) -> create an app -> add the
   WhatsApp product. This provisions a free test phone number and a temporary access token.
2. Note the **Phone Number ID** and **WhatsApp Business Account ID** from the API Setup page,
   and add your own number as a verified test recipient there.
3. Put the Phone Number ID, Business Account ID, and an access token into `.env` as
   `WHATSAPP_PHONE_NO_ID`, `WHATSAPP_BUSINESS_ACCOUNT_ID`, `WHATSAPP_ACCESS_TOKEN`.
   **Use a permanent System User token for anything beyond a quick test** — the temporary
   token from API Setup expires after 24 hours.
4. Submit a custom message template in WhatsApp Manager (Utility or Marketing category,
   Document header, named body variables) and wait for Meta's approval before real sends
   will work — see "Known limitations" below.
5. Production setup requires a verified webhook. `webhook/app.py` is a minimal Flask app
   that answers Meta's verification handshake and acknowledges (and discards) all events —
   replies are handled manually in the WhatsApp Business app, not by this system. Deploy it
   as a web service (e.g. Render: root directory `webhook`, build
   `pip install -r requirements.txt`, start `gunicorn app:app`) with
   `WHATSAPP_WEBHOOK_VERIFY_TOKEN` set, then enter `https://<host>/webhook` and the same
   token as the callback URL / verify token in the App Dashboard.

### 6. Fill in `.env`

Copy `.env.example` to `.env` and fill in everything from steps 2-5.

## Running

```bash
source env/bin/activate
python -m bot.main
```

Message the bot `/start`, then send a business card photo. `/cancel` aborts mid-flow at
any point.

## Deploying (Railway)

Two services from this repo in one Railway project:

- **bot** — root directory blank, start command `python -m bot.main`, no public domain.
  Variables: everything from `.env`, with `SHEETS_SERVICE_ACCOUNT_JSON` set to the full
  contents of the Sheets key file (`secrets/` isn't deployed).
- **webhook** — root directory `webhook`, start command
  `gunicorn app:app --bind 0.0.0.0:$PORT`, generate a public domain. Variable:
  `WHATSAPP_WEBHOOK_VERIFY_TOKEN`.

Only run one copy of the bot at a time — two pollers on the same Telegram token conflict.

## Known limitations / in-progress

- **WhatsApp template approval**: real brochure sends over WhatsApp require Meta to approve
  a custom template first (can take up to ~24h). `outbound/whatsapp_sender.py` has a
  `USE_TEST_TEMPLATE` flag that, when `True`, sends Meta's pre-approved `hello_world` demo
  message instead of the real payload. It is currently `False` (the template is approved).
- **Attachment size limits**: Workspace caps a message at 25MB, so `email_sender.py`
  refuses to send (with a clear in-chat message) if selected brochures total over ~15MB.
- **Email volume**: Workspace allows ~2,000 messages/day per sender (500/day while the
  Workspace subscription is still in its trial phase). WhatsApp's document header has its own (smaller) limit — compress large
  brochures if sends fail.
- **Gemini model note**: `gemini-3.5-flash-lite` uses fixed sampling and ignores the
  `temperature=0` setting in `extraction/gemini_client.py` (a benign warning, not an error).
- No database — conversation state lives in Telegram's per-chat `context.user_data` and is
  lost if the bot restarts mid-conversation (fine for this single-operator use case).
