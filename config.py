"""
Конфигурация бота. Все настройки берутся из переменных окружения (см. .env.example).
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
TONAPI_KEY: str = os.environ.get("TONAPI_KEY", "")
TONAPI_BASE: str = os.environ.get("TONAPI_BASE", "https://tonapi.io/v2")

# Сколько элементов показывать на одной "странице" в разделах Транзакции/NFT/Жетоны
PAGE_SIZE: int = int(os.environ.get("PAGE_SIZE", "8"))

# TTL кэша ответов TonAPI в секундах (снижает число запросов и риск упереться в rate limit)
CACHE_TTL: int = int(os.environ.get("CACHE_TTL", "20"))
CACHE_MAXSIZE: int = int(os.environ.get("CACHE_MAXSIZE", "512"))

# Таймауты и ретраи HTTP-запросов к TonAPI
HTTP_TIMEOUT: float = float(os.environ.get("HTTP_TIMEOUT", "15.0"))
HTTP_RETRIES: int = int(os.environ.get("HTTP_RETRIES", "3"))
HTTP_RETRY_BACKOFF: float = float(os.environ.get("HTTP_RETRY_BACKOFF", "0.6"))

LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

# Порт, на котором отдаём webapp/ton_ledger_report.html (Render передаёт его
# через переменную PORT автоматически — руками задавать не нужно).
PORT: int = int(os.environ.get("PORT", "10000"))

# Базовый URL, где отдаётся ton_ledger_report.html (production HTML-отчёт).
# Если задан — кнопка "Полный отчёт" открывает эту страницу как обычную ссылку
# в браузере, с адресом кошелька, подставленным в ?addr=..., без повторного ввода.
# Если не задан — бот показывает отчёт старым способом, прямо в чате.
REPORT_BASE_URL: str = os.environ.get("REPORT_BASE_URL", "")
