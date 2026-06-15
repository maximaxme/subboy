"""services/currency.py — USD→RUB exchange rate from the Central Bank of Russia.

Fetches https://www.cbr-xml-daily.ru/daily_json.js directly (this host is reachable
from the RU server and is not subject to the Telegram block, so it does NOT go
through the WARP proxy). The value is cached in memory for a few hours; if the API
is unavailable the last known rate (or a hardcoded fallback) is used.
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal

import aiohttp

logger = logging.getLogger(__name__)

CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
CACHE_TTL = 6 * 60 * 60  # seconds
FALLBACK_USD_RUB = Decimal("95")

_cached_rate: Decimal | None = None
_cached_at: float = 0.0


async def get_usd_rub() -> Decimal:
    """Return the current USD→RUB rate, cached for CACHE_TTL seconds."""
    global _cached_rate, _cached_at
    now = time.monotonic()
    if _cached_rate is not None and (now - _cached_at) < CACHE_TTL:
        return _cached_rate

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(CBR_URL) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        rate = Decimal(str(data["Valute"]["USD"]["Value"]))
        if rate <= 0:
            raise ValueError("non-positive rate")
        _cached_rate = rate
        _cached_at = now
        logger.info("USD→RUB rate updated: %s", rate)
        return rate
    except Exception as e:  # noqa: BLE001
        fallback = _cached_rate or FALLBACK_USD_RUB
        logger.warning("Failed to fetch USD→RUB rate (%s); using %s", e, fallback)
        return fallback
