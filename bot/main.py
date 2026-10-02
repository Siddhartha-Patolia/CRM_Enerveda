import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import config
from bot.conversation import card_conversation_handler, start

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


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
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(card_conversation_handler)
    application.add_error_handler(handle_error)

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
