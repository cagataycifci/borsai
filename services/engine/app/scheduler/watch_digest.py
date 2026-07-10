"""Stocks-to-watch digest: movers from watchlists + portfolio (Phase 8)."""

from __future__ import annotations

from app.data.models import Quote
from app.data.service import MarketDataService
from app.db.base import utcnow
from app.portfolio.service import PortfolioService
from app.scheduler.schemas import StocksToWatchDigest, WatchPick
from app.watchlists.service import WatchlistService


def _collect_symbols(watchlists: WatchlistService, portfolio: PortfolioService) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for wl in watchlists.list():
        for sym in wl.symbols:
            if sym not in seen:
                seen.add(sym)
                ordered.append(sym)
    for holding in portfolio.list():
        if holding.symbol not in seen:
            seen.add(holding.symbol)
            ordered.append(holding.symbol)
    return ordered


def _reason_for(quote: Quote) -> str:
    pct = quote.change_percent
    if pct is None:
        return "On your watchlist"
    if pct >= 3:
        return f"Strong gainer (+{pct:.1f}%)"
    if pct <= -3:
        return f"Sharp decline ({pct:.1f}%)"
    if pct >= 1:
        return f"Outperforming (+{pct:.1f}%)"
    if pct <= -1:
        return f"Weak session ({pct:.1f}%)"
    return "Stable — on your radar"


async def build_stocks_to_watch(
    watchlists: WatchlistService,
    portfolio: PortfolioService,
    market: MarketDataService,
    *,
    limit: int = 8,
) -> StocksToWatchDigest:
    symbols = _collect_symbols(watchlists, portfolio)
    quotes: list[Quote] = []
    for sym in symbols:
        q = await market.get_quote(sym)
        if q is not None and q.price is not None:
            quotes.append(q)

    # Rank by absolute daily move; stable names sink to the bottom.
    ranked = sorted(
        quotes,
        key=lambda q: abs(q.change_percent or 0),
        reverse=True,
    )[:limit]

    picks = [
        WatchPick(
            symbol=q.symbol,
            display_symbol=q.display_symbol,
            name=q.name,
            price=q.price,
            change_percent=q.change_percent,
            reason=_reason_for(q),
        )
        for q in ranked
    ]

    if not picks:
        overview = "Add symbols to your watchlists or portfolio to get a personalized digest."
    else:
        top = picks[0]
        overview = (
            f"Top mover: {top.display_symbol} ({top.change_percent:+.2f}%)"
            if top.change_percent is not None
            else f"Tracking {len(picks)} symbols from your lists."
        )

    return StocksToWatchDigest(
        overview=overview,
        picks=picks,
        generated_at=utcnow(),
    )
