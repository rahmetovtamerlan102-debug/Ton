"""
Хендлеры Telegram-бота.
"""
import logging

import httpx
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import keyboards
from services import tonapi
from services.formatting import esc, fmt_event_line, fmt_nft_line, fmt_jetton_amount, fmt_ts, nano_to_ton

logger = logging.getLogger(__name__)


def is_probably_ton_address(text: str) -> bool:
    text = text.strip()
    if text.endswith(".ton"):
        return True
    if text.startswith("0:") and len(text) == 66:
        return True
    if len(text) in (47, 48) and text[0] in "EUku":
        return True
    return False


# ---------------------------------------------------------------------------
# Построение экранов
# ---------------------------------------------------------------------------

async def build_main_screen(client: httpx.AsyncClient, address: str) -> str:
    account = await tonapi.get_account(client, address)

    balance = nano_to_ton(account.get("balance", 0))
    status = account.get("status", "unknown")
    is_wallet = account.get("is_wallet", False)
    interfaces = account.get("interfaces") or []
    last_activity = account.get("last_activity")
    memo_required = account.get("memo_required", False)

    lines = [
        f"<b>💼 Кошелёк:</b> <code>{esc(address)}</code>",
        f"<b>💰 Баланс:</b> {balance:.4f} TON",
        f"<b>Статус:</b> {esc(status)}" + (" ✅" if status == "active" else ""),
        f"<b>Тип:</b> {'кошелёк' if is_wallet else 'смарт-контракт'}"
        + (f" ({esc(', '.join(interfaces))})" if interfaces else ""),
    ]
    if last_activity:
        lines.append(f"<b>🕒 Последняя активность:</b> {fmt_ts(last_activity)}")
    if memo_required:
        lines.append("⚠️ Для переводов на этот адрес требуется memo/tag")

    lines.append("\nПолный отчёт по транзакциям и NFT — в меню ниже 👇")
    return "\n".join(lines)


async def build_tx_screen(client: httpx.AsyncClient, address: str, offset: int):
    data = await tonapi.get_events(client, address, limit=config.PAGE_SIZE + 1)
    events = data.get("events", []) if isinstance(data, dict) else []
    page = events[offset: offset + config.PAGE_SIZE]
    has_more = len(events) > offset + config.PAGE_SIZE

    header = f"<b>📜 Полный отчёт — транзакции</b> ({offset + 1}–{offset + len(page)}):\n"
    if not page:
        body = "Транзакций не найдено."
    else:
        body = "\n".join(fmt_event_line(ev) for ev in page)
    return header + "\n" + body, has_more


async def build_nft_screen(client: httpx.AsyncClient, address: str, offset: int):
    data = await tonapi.get_nfts(client, address, limit=config.PAGE_SIZE + 1, offset=offset)
    items = data.get("nft_items", []) if isinstance(data, dict) else []
    has_more = len(items) > config.PAGE_SIZE
    items = items[:config.PAGE_SIZE]

    if offset == 0 and not items:
        header = "<b>🖼 NFT</b>\n"
        body = "На этом кошельке NFT не найдены."
        return header + body, False

    header = f"<b>🖼 NFT</b> ({offset + 1}–{offset + len(items)}):\n"
    body = "\n\n".join(fmt_nft_line(item) for item in items)
    return header + "\n" + body, has_more


async def build_jetton_screen(client: httpx.AsyncClient, address: str, offset: int):
    data = await tonapi.get_jettons(client, address)
    balances = data.get("balances", []) if isinstance(data, dict) else []
    page = balances[offset: offset + config.PAGE_SIZE]
    has_more = len(balances) > offset + config.PAGE_SIZE

    header = f"<b>💎 Жетоны</b> ({offset + 1}–{offset + len(page)} из {len(balances)}):\n"
    if not page:
        body = "Жетонов не найдено."
    else:
        rows = []
        for b in page:
            jetton = b.get("jetton", {}) or {}
            symbol = jetton.get("symbol", "???")
            decimals = jetton.get("decimals", 9)
            amount = fmt_jetton_amount(b.get("balance", 0), decimals)
            rows.append(f"• <b>{amount} {esc(symbol)}</b>")
        body = "\n".join(rows)
    return header + "\n" + body, has_more


# ---------------------------------------------------------------------------
# Команды
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли адрес TON-кошелька (из Tonkeeper) или .ton-домен — "
        "сразу покажу баланс и статус, а транзакции и NFT будут доступны через меню ниже.\n\n"
        "Пример:\nEQD...ваш_адрес...\nили\nexample.ton"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь TON-адрес (EQ.../UQ...) или .ton домен.\n"
        "/start — приветствие\n/help — эта справка"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if not is_probably_ton_address(text):
        await update.message.reply_text(
            "Похоже, это не TON-адрес и не .ton домен. Пример:\n"
            "EQD4FPq-PRDieyQKkizFTRtSDyucUIqrj0v_zXJmqaDp6_0t\nили\nname.ton"
        )
        return

    status_msg = await update.message.reply_text("⏳ Ищу данные...")
    async with httpx.AsyncClient() as client:
        try:
            address = await tonapi.resolve_address(client, text)
            context.user_data["address"] = address
            report = await build_main_screen(client, address)
            await status_msg.edit_text(
                report, parse_mode=ParseMode.HTML, reply_markup=keyboards.main_keyboard(address),
                disable_web_page_preview=True,
            )
        except tonapi.AccountNotFound:
            await status_msg.edit_text("❌ Аккаунт не найден. Проверь адрес.")
        except tonapi.TonApiError as e:
            logger.warning("TonAPI error: %s", e)
            await status_msg.edit_text(f"❌ TonAPI временно недоступен ({e}). Попробуй позже.")
        except Exception as e:
            logger.exception("Unexpected error handling message")
            await status_msg.edit_text(f"❌ Не получилось получить данные: {e}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    address = context.user_data.get("address")
    if not address:
        await query.edit_message_text("Сессия устарела. Пришли адрес кошелька заново.")
        return

    section, offset_str = query.data.split(":")
    offset = int(offset_str)

    async with httpx.AsyncClient() as client:
        try:
            if section == "main":
                text = await build_main_screen(client, address)
                await query.edit_message_text(
                    text, parse_mode=ParseMode.HTML, reply_markup=keyboards.main_keyboard(address),
                    disable_web_page_preview=True,
                )
                return

            builders = {"tx": build_tx_screen, "nft": build_nft_screen, "jetton": build_jetton_screen}
            builder = builders.get(section)
            if builder is None:
                return

            text, has_more = await builder(client, address, offset)
            await query.edit_message_text(
                text, parse_mode=ParseMode.HTML,
                reply_markup=keyboards.section_keyboard(section, offset, has_more),
                disable_web_page_preview=True,
            )
        except tonapi.AccountNotFound:
            await query.edit_message_text("❌ Аккаунт не найден.", reply_markup=keyboards.main_keyboard(address))
        except tonapi.TonApiError as e:
            await query.edit_message_text(f"❌ TonAPI временно недоступен ({e}).", reply_markup=keyboards.main_keyboard(address))
        except Exception as e:
            logger.exception("Unexpected error in callback")
            await query.edit_message_text(f"❌ Ошибка: {e}", reply_markup=keyboards.main_keyboard(address))


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled exception while processing update: %s", update, exc_info=context.error)
