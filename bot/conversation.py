import asyncio
import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.keyboards import brochure_keyboard, confirmation_keyboard
from brochure_catalog import list_brochures
from extraction.gemini_client import (
    ExtractionError,
    ExtractionTimeoutError,
    ModelUnavailableError,
    RateLimitExceededError,
    extract,
)

from outbound.email_sender import exceeds_size_limit, send as send_email
from outbound.whatsapp_sender import send as send_whatsapp
from sheets.sheet_logger import append_row
from token_logger import log_usage

logger = logging.getLogger(__name__)

BROCHURE_SELECT, CONFIRM_PAYLOAD, EDITING_FIELD = range(3)

_FIELD_LABELS = {"name": "Name", "company": "Company", "phone": "Phone", "email": "Email"}


async def _maybe_send(should_send: bool, func, *args) -> bool:
    if not should_send:
        return False
    return await asyncio.to_thread(func, *args)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! Send me a photo of a business card and I'll take it from there."
    )



def _render_confirmation_text(user_data: dict) -> str:
    contact = user_data.get("contact", {})
    selected_keys = user_data.get("selected", set())
    labels = [b.label for b in list_brochures() if b.key in selected_keys]
    return (
        "Please review before sending:\n"
        f"Name: {contact.get('name') or 'not set'}\n"
        f"Company: {contact.get('company') or 'not set'}\n"
        f"Phone: {contact.get('phone') or 'not set'}\n"
        f"Email: {contact.get('email') or 'not set'}\n"
        f"Brochures: {', '.join(labels) or 'none selected'}"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📇 Reading the card...")

    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = bytes(await file.download_as_bytearray())

    try:
        contact, token_usage = extract(image_bytes)
    except ExtractionTimeoutError:
        logger.exception("Gemini extraction timed out")
        await update.message.reply_text(
            "That's taking too long to process. Please try again in a moment."
        )
        return ConversationHandler.END
    except RateLimitExceededError:
        logger.exception("Gemini quota/rate limit hit")
        await update.message.reply_text(
            "I've hit my Gemini API usage limit, so I can't process cards right now. "
            "Please try again later."
        )
        return ConversationHandler.END
    except ModelUnavailableError:
        logger.exception("Gemini model unavailable")
        await update.message.reply_text(
            "The AI model I use to read cards isn't available right now — this is a "
            "configuration issue on my end, not your photo. I've logged the details."
        )
        return ConversationHandler.END
    except ExtractionError:
        logger.exception("Gemini extraction call failed")
        await update.message.reply_text(
            "I hit a technical error trying to process that (not your photo's fault). "
            "I've logged the details; please try again shortly."
        )
        return ConversationHandler.END

    log_usage(
        update.effective_user.full_name,
        token_usage.input_tokens,
        token_usage.output_tokens,
        token_usage.total_tokens,
    )

    if contact.is_empty():
        await update.message.reply_text(
            "I couldn't pull any contact details from that image. Could you send a "
            "clearer photo, or confirm whether the card actually has a name, company, "
            "phone, or email printed on it?"
        )
        return ConversationHandler.END

    context.user_data["contact"] = {
        "name": contact.name,
        "company": contact.company,
        "phone": contact.phone,
        "email": contact.email,
    }
    context.user_data["selected"] = set()
    context.user_data["sender_name"] = update.effective_user.full_name

    await update.message.reply_text(
        "Here's what I found. Pick which brochures to send:",
        reply_markup=brochure_keyboard(context.user_data["selected"]),
    )
    return BROCHURE_SELECT


async def handle_brochure_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == "continue":
        selected = context.user_data.get("selected", set())
        if not selected:
            await query.answer("Select at least one brochure first.", show_alert=True)
            return BROCHURE_SELECT
        await query.answer()
        await query.edit_message_text(
            _render_confirmation_text(context.user_data),
            reply_markup=confirmation_keyboard(),
        )
        return CONFIRM_PAYLOAD

    await query.answer()
    key = data.split(":", 1)[1]
    selected = context.user_data.setdefault("selected", set())
    if key in selected:
        selected.discard(key)
    else:
        selected.add(key)
    await query.edit_message_reply_markup(reply_markup=brochure_keyboard(selected))
    return BROCHURE_SELECT


async def handle_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("Outreach cancelled. Send a business card image to begin.")
        return ConversationHandler.END

    if data == "confirm":
        contact = context.user_data.get("contact", {})
        selected_keys = context.user_data.get("selected", set())
        brochures = [b for b in list_brochures() if b.key in selected_keys]
        brochure_labels = ", ".join(b.label for b in brochures)
        sender_name = context.user_data.get("sender_name")

        email_line = None
        if not contact.get("email"):
            email_should_send = False
            email_line = "✉️ No email on this card — skipped sending (use Edit Email to add one before confirming)."
        elif exceeds_size_limit(brochures):
            email_should_send = False
            email_line = (
                "⚠️ Selected brochures are too large to email (Gmail's limit is ~20MB "
                "total) — try selecting fewer or smaller brochures."
            )
        else:
            email_should_send = True

        whatsapp_line = None
        if not contact.get("phone"):
            whatsapp_should_send = False
            whatsapp_line = "📱 No phone number on this card — skipped WhatsApp."
        else:
            whatsapp_should_send = True

        email_sent, whatsapp_sent = await asyncio.gather(
            _maybe_send(email_should_send, send_email, contact, brochures, sender_name),
            _maybe_send(whatsapp_should_send, send_whatsapp, contact, brochures, sender_name),
        )

        if email_line is None:
            email_line = "✉️ Email sent." if email_sent else "⚠️ Email failed to send — check the logs."
        if whatsapp_line is None:
            whatsapp_line = "📱 WhatsApp sent." if whatsapp_sent else "⚠️ WhatsApp failed to send — check the logs."

        sheet_ok = None
        if email_sent or whatsapp_sent:
            sheet_ok = append_row(
                contact.get("company"),
                contact.get("name"),
                contact.get("phone"),
                contact.get("email"),
                brochure_labels,
                sender_name,
                "Sent" if email_sent else "Failed",
                "Sent" if whatsapp_sent else "Failed",
            )

        lines = [email_line, whatsapp_line]
        if sheet_ok is not None:
            lines.append("✅ Logged to sheet." if sheet_ok else "⚠️ Failed to log to sheet — check the logs.")
        await query.edit_message_text("\n".join(lines))
        context.user_data.clear()
        return ConversationHandler.END

    if data.startswith("edit:"):
        field = data.split(":", 1)[1]
        context.user_data["editing_field"] = field
        await query.edit_message_text(f"Send me the corrected {_FIELD_LABELS.get(field, field)}.")
        return EDITING_FIELD

    return CONFIRM_PAYLOAD


async def handle_field_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.get("editing_field")
    value = update.message.text.strip()
    contact = context.user_data.setdefault("contact", {})
    contact[field] = value
    context.user_data.pop("editing_field", None)

    await update.message.reply_text(
        _render_confirmation_text(context.user_data),
        reply_markup=confirmation_keyboard(),
    )
    return CONFIRM_PAYLOAD


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Outreach cancelled. Send the business card image to begin.")
    return ConversationHandler.END


card_conversation_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.PHOTO, handle_photo)],
    states={
        BROCHURE_SELECT: [CallbackQueryHandler(handle_brochure_callback)],
        CONFIRM_PAYLOAD: [CallbackQueryHandler(handle_confirm_callback)],
        EDITING_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_edit)],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
)
