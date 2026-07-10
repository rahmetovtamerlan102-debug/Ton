"""
Инлайн-клавиатуры бота.
"""
from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config


def main_keyboard(address: str) -> InlineKeyboardMarkup:
    if config.REPORT_BASE_URL:
        report_url = f"{config.REPORT_BASE_URL}?addr={quote(address)}"
        # Обычная url-кнопка: открывает страницу в браузере (с адресной строкой),
        # а не как Telegram Mini App поверх чата.
        report_button = InlineKeyboardButton("📜 Полный отчёт (транзакции)", url=report_url)
    else:
        # Фолбэк, если хостинг HTML-страницы ещё не настроен (см. REPORT_BASE_URL в .env):
        # показываем отчёт по транзакциям прямо в чате, как раньше.
        report_button = InlineKeyboardButton("📜 Полный отчёт (транзакции)", callback_data="tx:0")

    return InlineKeyboardMarkup(
        [
            [report_button],
            [
                InlineKeyboardButton("🖼 NFT", callback_data="nft:0"),
                InlineKeyboardButton("💎 Жетоны", callback_data="jetton:0"),
            ],
            [InlineKeyboardButton("🔄 Обновить баланс", callback_data="main:0")],
        ]
    )


def section_keyboard(section: str, offset: int, has_more: bool) -> InlineKeyboardMarkup:
    nav_row = []
    if offset > 0:
        nav_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"{section}:{max(0, offset - config.PAGE_SIZE)}")
        )
    if has_more:
        nav_row.append(InlineKeyboardButton("Ещё ➡️", callback_data=f"{section}:{offset + config.PAGE_SIZE}"))

    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append([InlineKeyboardButton("🏠 Назад к балансу", callback_data="main:0")])
    return InlineKeyboardMarkup(rows)
