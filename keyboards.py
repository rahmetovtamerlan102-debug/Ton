"""
Инлайн-клавиатуры бота.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📜 Полный отчёт (транзакции)", callback_data="tx:0")],
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
