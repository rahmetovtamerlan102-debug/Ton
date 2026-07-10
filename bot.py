"""
Точка входа. Собирает Application, настраивает логирование и запускает polling.
"""
import logging
import sys

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import config
import handlers


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        stream=sys.stdout,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def build_application() -> Application:
    if not config.BOT_TOKEN:
        raise SystemExit("Не задан BOT_TOKEN. Проверь .env / переменные окружения.")

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_handler(CallbackQueryHandler(handlers.handle_callback))
    app.add_error_handler(handlers.on_error)

    return app


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    app = build_application()
    logger.info("Бот запущен, ожидаю сообщения (polling)...")
    app.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
