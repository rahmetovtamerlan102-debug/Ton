"""
Тонкий асинхронный клиент к TonAPI (https://tonapi.io) с:
- автоматическими ретраями при сетевых сбоях / 5xx / 429
- TTL-кэшем ответов, чтобы не долбить API одинаковыми запросами
- едиными исключениями для слоя хендлеров
"""
import asyncio
import logging
from typing import Any, Optional

import httpx
from cachetools import TTLCache

import config

logger = logging.getLogger(__name__)

_cache: TTLCache = TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL)
_headers = {"Authorization": f"Bearer {config.TONAPI_KEY}"} if config.TONAPI_KEY else {}


class TonApiError(Exception):
    """Базовая ошибка обращения к TonAPI."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class AccountNotFound(TonApiError):
    pass


def _cache_key(path: str, params: dict) -> str:
    parts = ",".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{path}?{parts}"


async def _request(client: httpx.AsyncClient, path: str, params: Optional[dict] = None) -> Any:
    params = params or {}
    key = _cache_key(path, params)
    if key in _cache:
        return _cache[key]

    url = f"{config.TONAPI_BASE}{path}"
    last_exc: Optional[Exception] = None

    for attempt in range(1, config.HTTP_RETRIES + 1):
        try:
            resp = await client.get(url, headers=_headers, params=params, timeout=config.HTTP_TIMEOUT)
            if resp.status_code == 404:
                raise AccountNotFound("Аккаунт/сущность не найдены", status_code=404)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
            resp.raise_for_status()
            data = resp.json()
            _cache[key] = data
            return data
        except AccountNotFound:
            raise
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_exc = exc
            if attempt < config.HTTP_RETRIES:
                delay = config.HTTP_RETRY_BACKOFF * (2 ** (attempt - 1))
                logger.warning("TonAPI %s попытка %s/%s не удалась (%s), повтор через %.1fs",
                               path, attempt, config.HTTP_RETRIES, exc, delay)
                await asyncio.sleep(delay)
            else:
                logger.error("TonAPI %s: все попытки исчерпаны", path)

    status = getattr(getattr(last_exc, "response", None), "status_code", None)
    raise TonApiError(f"TonAPI недоступен: {last_exc}", status_code=status)


async def resolve_address(client: httpx.AsyncClient, raw: str) -> str:
    raw = raw.strip()
    if raw.endswith(".ton"):
        data = await _request(client, f"/dns/{raw}")
        wallet = (data or {}).get("wallet") or {}
        addr = wallet.get("address")
        if not addr:
            raise TonApiError(f"Домен {raw} не привязан ни к одному кошельку")
        return addr
    return raw


async def get_account(client: httpx.AsyncClient, address: str) -> dict:
    return await _request(client, f"/accounts/{address}")


async def get_events(client: httpx.AsyncClient, address: str, limit: int, before_lt: Optional[int] = None) -> dict:
    params = {"limit": limit}
    if before_lt:
        params["before_lt"] = before_lt
    return await _request(client, f"/accounts/{address}/events", params)


async def get_nfts(client: httpx.AsyncClient, address: str, limit: int, offset: int) -> dict:
    params = {"limit": limit, "offset": offset, "indirect_ownership": "false"}
    return await _request(client, f"/accounts/{address}/nfts", params)


async def get_jettons(client: httpx.AsyncClient, address: str) -> dict:
    return await _request(client, f"/accounts/{address}/jettons", {"currencies": "usd"})


async def get_nft_item(client: httpx.AsyncClient, nft_address: str) -> dict:
    return await _request(client, f"/nfts/{nft_address}")
