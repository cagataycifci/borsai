"""Morning market summary builder (Phase 8).

Assembles benchmark quotes + recent headlines into a structured report. When an
AI provider is configured, the narrative overview is enhanced by the model;
otherwise a deterministic template is used so the feature works offline.
"""

from __future__ import annotations

import json

from app.ai.base import AIProvider
from app.data.models import Quote
from app.data.service import MarketDataService
from app.db.base import utcnow
from app.news.schemas import NewsArticle
from app.news.service import NewsService
from app.scheduler.schemas import MorningSummary, NewsHeadline, QuoteSnapshot, ReportRegion

BENCHMARKS: dict[ReportRegion, list[str]] = {
    ReportRegion.US: ["SPY", "QQQ", "DIA", "IWM"],
    ReportRegion.TR: ["XU100.IS", "ASELS.IS", "THYAO.IS", "GARAN.IS"],
    ReportRegion.GLOBAL: ["SPY", "XU100.IS", "EEM", "GLD"],
}

REGION_TITLES: dict[ReportRegion, str] = {
    ReportRegion.US: "US Morning Market Summary",
    ReportRegion.TR: "BIST Morning Market Summary",
    ReportRegion.GLOBAL: "Global Morning Market Summary",
}

MORNING_SYSTEM = (
    "You are a financial markets editor writing a concise morning briefing for a "
    "desktop terminal. Given benchmark quotes and headlines, write a 3–5 sentence "
    "overview and 3–5 short bullet highlights. Be factual and neutral. This is "
    "informational, not financial advice. Respond with ONLY a JSON object:\n"
    '{"overview": "...", "highlights": ["...", "..."]}'
)


def _quote_snapshot(q: Quote) -> QuoteSnapshot:
    return QuoteSnapshot(
        symbol=q.symbol,
        display_symbol=q.display_symbol,
        name=q.name,
        price=q.price,
        change=q.change,
        change_percent=q.change_percent,
        currency=q.currency,
    )


def _template_overview(
    region: ReportRegion, benchmarks: list[QuoteSnapshot]
) -> tuple[str, list[str]]:
    """Deterministic fallback when AI is unavailable."""
    movers = sorted(
        [b for b in benchmarks if b.change_percent is not None],
        key=lambda b: abs(b.change_percent or 0),
        reverse=True,
    )
    if not movers:
        overview = f"No benchmark data available for the {region.value.upper()} session."
        return overview, []

    leader = movers[0]
    direction = "up" if (leader.change_percent or 0) >= 0 else "down"
    overview = (
        f"{REGION_TITLES[region]}: {leader.display_symbol} leads benchmarks, "
        f"{direction} {abs(leader.change_percent or 0):.2f}%."
    )
    highlights = [
        (
            f"{b.display_symbol}: {b.change_percent:+.2f}%"
            if b.change_percent is not None
            else b.display_symbol
        )
        for b in benchmarks[:4]
        if b.change_percent is not None
    ]
    return overview, highlights


async def _ai_enhance(
    provider: AIProvider,
    region: ReportRegion,
    benchmarks: list[QuoteSnapshot],
    headlines: list[NewsHeadline],
) -> tuple[str, list[str]] | None:
    context = {
        "region": region.value,
        "benchmarks": [b.model_dump() for b in benchmarks],
        "headlines": [h.model_dump() for h in headlines[:8]],
    }
    prompt = (
        "Write a morning market briefing from this data:\n\n"
        + json.dumps(context, indent=2, default=str)
        + "\n\nReturn the JSON object now."
    )
    try:
        raw = await provider.complete(MORNING_SYSTEM, prompt, max_tokens=800)
        data = json.loads(_strip_json(raw))
        overview = str(data.get("overview", "")).strip()
        highlights = [str(h).strip() for h in data.get("highlights", []) if str(h).strip()]
        if overview:
            return overview, highlights
    except Exception:  # noqa: BLE001 — AI enhancement is best-effort
        return None
    return None


def _strip_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


async def build_morning_summary(
    region: ReportRegion,
    market: MarketDataService,
    news: NewsService,
    *,
    ai_provider: AIProvider | None = None,
) -> MorningSummary:
    symbols = BENCHMARKS[region]
    benchmarks: list[QuoteSnapshot] = []
    for sym in symbols:
        quote = await market.get_quote(sym)
        if quote is not None:
            benchmarks.append(_quote_snapshot(quote))

    articles: list[NewsArticle] = news.list_recent(limit=12)
    headlines = [
        NewsHeadline(title=a.title, source=a.source, url=a.url) for a in articles[:8]
    ]

    overview, highlights = _template_overview(region, benchmarks)
    ai_enhanced = False

    if ai_provider is not None:
        try:
            enhanced = await _ai_enhance(ai_provider, region, benchmarks, headlines)
            if enhanced:
                overview, highlights = enhanced
                ai_enhanced = True
        finally:
            await ai_provider.aclose()

    return MorningSummary(
        region=region,
        title=REGION_TITLES[region],
        overview=overview,
        benchmarks=benchmarks,
        headlines=headlines,
        highlights=highlights,
        ai_enhanced=ai_enhanced,
        generated_at=utcnow(),
    )
