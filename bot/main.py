import logging

from telegram import Update
from telegram.ext import Application, ApplicationHandlerStop, CommandHandler, ContextTypes, TypeHandler

import config
from bot.conversation import card_conversation_handler, start
from bot.per_user_processor import PerUserUpdateProcessor

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
# httpx logs every request URL at INFO, and Telegram URLs contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Upper bound on updates actively being processed at once, across all users.
_MAX_CONCURRENT_UPDATES = 8


async def restrict_to_staff(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs before every other handler; drops updates from users not on the allowlist.

    The bot sends email and WhatsApp from company accounts, so it must not be usable by
    anyone who finds its username. An empty ALLOWED_TELEGRAM_USER_IDS leaves it open.
    """
    if not config.ALLOWED_TELEGRAM_USER_IDS or not isinstance(update, Update):
        return
    user = update.effective_user
    if user and user.id in config.ALLOWED_TELEGRAM_USER_IDS:
        return

    user_id = user.id if user else "unknown"
    logger.warning("Blocked update from non-staff Telegram user %s", user_id)
    text = f"This bot is private. Your Telegram ID is {user_id} — ask the admin to add it."
    if update.callback_query:
        await update.callback_query.answer(text, show_alert=True)
    elif update.effective_message:
        await update.effective_message.reply_text(text)
    raise ApplicationHandlerStop


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception while processing an update", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Something went wrong on my end. Please try again."
            )
        except Exception:
            logger.exception("Failed to notify user about the unhandled error")


def main() -> None:
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .concurrent_updates(PerUserUpdateProcessor(_MAX_CONCURRENT_UPDATES))
        .build()
    )

    application.add_handler(TypeHandler(Update, restrict_to_staff), group=-1)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(card_conversation_handler)
    application.add_error_handler(handle_error)

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
