"""
Точка входа. Собирает Application, настраивает логирование и запускает polling.
Параллельно поднимает лёгкий HTTP-сервер, отдающий webapp/ton_ledger_report.html —
чтобы бот и HTML-отчёт жили в одном Render-сервисе на одном порту.
"""
import functools
import http.server
import logging
import sys
import threading
from pathlib import Path

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import config
import handlers

WEBAPP_DIR = Path(__file__).parent / "webapp"


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        stream=sys.stdout,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def start_static_server(logger: logging.Logger) -> None:
    """Отдаёт файлы из webapp/ (в т.ч. ton_ledger_report.html) на config.PORT.

    Render требует, чтобы Web Service слушал порт — заодно на этом же порту
    отдаём HTML-отчёт, так что второй сервис для него не нужен.
    """
    if not WEBAPP_DIR.exists():
        logger.warning("Папка webapp/ не найдена — статический сервер не запущен")
        return

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WEBAPP_DIR))
    server = http.server.ThreadingHTTPServer(("0.0.0.0", config.PORT), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Статический сервер webapp/ запущен на порту %s", config.PORT)


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

    start_static_server(logger)

    app = build_application()
    logger.info("Бот запущен, ожидаю сообщения (polling)...")
    app.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
