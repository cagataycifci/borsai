"""Builds the MarketDataService from the configured provider order + secrets.

Keeps provider wiring (which adapters, in what order, with which keys) out of the
app bootstrap. Re-callable so the service can be rebuilt when settings change.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.data.base import MarketDataAdapter
from app.data.providers.finnhub_adapter import FinnhubAdapter
from app.data.providers.yfinance_adapter import YFinanceAdapter
from app.data.quote_store import SqliteQuoteStore
from app.data.service import MarketDataService
from app.settings.service import SecretsService, SettingsService

logger = get_logger(__name__)


def build_market_data_service(
    settings_service: SettingsService, secrets_service: SecretsService
) -> tuple[MarketDataService, list[FinnhubAdapter]]:
    """Return (service, closeables). ``closeables`` are adapters holding network
    clients that must be closed on shutdown."""
    order = settings_service.get_provider_order()
    adapters: list[MarketDataAdapter] = []
    closeables: list[FinnhubAdapter] = []

    for name in order:
        if name == "yfinance":
            adapters.append(YFinanceAdapter())
        elif name == "finnhub":
            key = secrets_service.get("finnhub")
            if key:
                fh = FinnhubAdapter(key)
                adapters.append(fh)
                closeables.append(fh)
            else:
                logger.info("Finnhub configured in order but no API key set; skipping.")

    # Always guarantee at least yfinance so the service can serve BIST + a fallback.
    if not any(a.name == "yfinance" for a in adapters):
        adapters.append(YFinanceAdapter())

    logger.info("Active data providers: %s", [a.name for a in adapters])
    return MarketDataService(adapters, quote_store=SqliteQuoteStore()), closeables
