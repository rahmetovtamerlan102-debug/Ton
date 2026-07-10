"""
Форматирование данных TonAPI в человекочитаемый вид (для сообщений в Telegram, HTML-разметка).
"""
import html
from datetime import datetime, timezone
from typing import Optional


def nano_to_ton(nanotons) -> float:
    try:
        return int(nanotons) / 1_000_000_000
    except (TypeError, ValueError):
        return 0.0


def fmt_ts(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    except (TypeError, ValueError, OSError):
        return "неизвестно"


def esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def fmt_jetton_amount(raw_balance, decimals) -> str:
    try:
        value = int(raw_balance) / (10 ** int(decimals))
        text = f"{value:,.4f}".rstrip("0").rstrip(".")
        return text if text else "0"
    except (TypeError, ValueError, ZeroDivisionError):
        return str(raw_balance)


MARKET_NAMES = {
    "getgems.io": "GetGems",
    "fragment.com": "Fragment",
    "disintar.io": "Disintar",
    "tonkeeper.com": "Tonkeeper",
}


def fmt_nft_listing_status(item: dict) -> str:
    """
    Возвращает статус NFT: выставлен ли он сейчас на продажу/аукцион (по данным маркетплейсов),
    либо просто находится на балансе владельца без активного лота.
    """
    sale = item.get("sale")
    if not sale:
        return "— не выставлен на продажу"

    market_addr = (sale.get("market") or {}).get("name") or sale.get("market_name") or ""
    market_name = MARKET_NAMES.get(market_addr.lower(), market_addr) if market_addr else "маркетплейс"

    price = sale.get("price") or {}
    amount = nano_to_ton(price.get("value", 0))
    token = (price.get("token_name") or "TON").upper()

    sale_type = sale.get("sale_type") or sale.get("type") or "fix_price"
    if "auction" in str(sale_type).lower():
        return f"🔨 На аукционе на {esc(market_name)}, текущая ставка {amount:.2f} {esc(token)}"
    return f"🏷 Выставлен на продажу на {esc(market_name)} за {amount:.2f} {esc(token)}"


def fmt_nft_line(item: dict) -> str:
    meta = item.get("metadata", {}) or {}
    title = meta.get("name") or item.get("address", "NFT")
    collection = (item.get("collection") or {}).get("name")
    verified = (item.get("collection") or {}).get("is_approved", True)

    line = f"• <b>{esc(title)}</b>"
    if collection:
        line += f" — {esc(collection)}"
    if not verified:
        line += " ⚠️ непроверенная коллекция"
    line += f"\n   {fmt_nft_listing_status(item)}"
    return line


def fmt_event_line(ev: dict) -> str:
    ts = fmt_ts(ev.get("timestamp"))
    actions = ev.get("actions", []) or []
    descr: Optional[str] = None
    if actions:
        descr = (actions[0].get("simple_preview") or {}).get("description") or actions[0].get("type")
    descr = descr or ev.get("event_id", "событие")
    prefix = "🚫 " if ev.get("is_scam") else "• "
    return f"{prefix}{ts} — {esc(descr)[:150]}"
