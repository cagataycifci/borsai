"""AI service: stock analysis, streaming chat, and news classification.

Composes the data, technical, and news layers into a context bundle, prompts the
configured :class:`AIProvider`, and returns typed results. The provider is built
fresh per request from settings + the encrypted secrets store, so a key entered
in the Settings UI takes effect without an engine restart.

Generated analysis reports are persisted to ``ai_reports`` for history and quick
re-display.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable

from sqlalchemy import select

from app.ai.base import AIProvider, ProviderError
from app.ai.prompts import (
    ANALYSIS_SYSTEM,
    CHAT_SYSTEM,
    CLASSIFY_SYSTEM,
    build_analysis_prompt,
    build_classify_prompt,
)
from app.ai.providers.anthropic_adapter import DEFAULT_MODEL as ANTHROPIC_MODEL
from app.ai.providers.gemini_adapter import DEFAULT_MODEL as GEMINI_MODEL
from app.ai.providers.ollama_adapter import DEFAULT_MODEL as OLLAMA_MODEL
from app.ai.providers.openai_adapter import DEFAULT_MODEL as OPENAI_MODEL
from app.ai.schemas import (
    AIStatus,
    AnalysisReport,
    ChatMessage,
    NewsClassification,
    Sentiment,
)
from app.core.logging import get_logger
from app.data.base import Interval, Range
from app.data.service import MarketDataService
from app.db.base import utcnow
from app.db.models import AiReportRow
from app.db.session import session_scope
from app.news.service import NewsService
from app.settings.service import AI_PROVIDERS, SecretsService, SettingsService
from app.technical import compute_indicators

logger = get_logger(__name__)

# Provider -> its default model (used to report status / pick a model).
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": ANTHROPIC_MODEL,
    "openai": OPENAI_MODEL,
    "gemini": GEMINI_MODEL,
    "ollama": OLLAMA_MODEL,
}

# Compact indicator spec summarized into the analysis context bundle.
ANALYSIS_INDICATORS = "sma:20,sma:50,ema:20,rsi,macd,bbands:20:2,atr"

ProviderFactory = Callable[[SettingsService, SecretsService], AIProvider | None]


class AIService:
    def __init__(
        self,
        settings_service: SettingsService,
        secrets_service: SecretsService,
        market_data: MarketDataService,
        news: NewsService,
        provider_factory: ProviderFactory,
    ) -> None:
        self._settings = settings_service
        self._secrets = secrets_service
        self._market = market_data
        self._news = news
        self._build_provider = provider_factory

    # -- status -------------------------------------------------------------
    def status(self) -> AIStatus:
        name = self._settings.get_active_ai_provider()
        configured = {p: self._secrets.is_configured(p) for p in AI_PROVIDERS}
        needs_key = AI_PROVIDERS.get(name, True)
        ready = (not needs_key) or configured.get(name, False)
        stored = self._settings.get_ai_model()
        if name == "gemini":
            from app.ai.providers.gemini_adapter import resolve_gemini_model

            model = resolve_gemini_model(stored)
        else:
            model = stored or DEFAULT_MODELS.get(name, "")
        return AIStatus(
            ready=ready,
            active_provider=name,
            model=model,
            configured=configured,
            providers=list(AI_PROVIDERS),
        )

    def _provider(self) -> AIProvider:
        provider = self._build_provider(self._settings, self._secrets)
        if provider is None:
            raise ProviderError(
                "No AI provider configured. Add an API key in Settings."
            )
        return provider

    # -- stock analysis -----------------------------------------------------
    async def analyze(self, symbol: str) -> AnalysisReport:
        symbol = self._market.normalize(symbol)
        context = await self._context_bundle(symbol)
        provider = self._provider()
        try:
            raw = await provider.complete(
                ANALYSIS_SYSTEM, build_analysis_prompt(context), max_tokens=1500
            )
        finally:
            await provider.aclose()

        data = _parse_json_object(raw)
        report = AnalysisReport(
            symbol=symbol,
            provider=provider.name,
            model=provider.model,
            sentiment=_coerce_sentiment(data.get("sentiment")),
            rating=_coerce_rating(data.get("rating")),
            summary=str(data.get("summary", "")).strip(),
            key_points=_str_list(data.get("key_points")),
            risks=_str_list(data.get("risks")),
            technical_outlook=str(data.get("technical_outlook", "")).strip(),
            recommendation=str(data.get("recommendation", "")).strip(),
            created_at=utcnow(),
        )
        self._persist(report)
        return report

    async def _context_bundle(self, symbol: str) -> dict[str, object]:
        quote = await self._market.get_quote(symbol)
        candles = await self._market.get_history(symbol, Interval.D1, Range.Y1)
        indicators = compute_indicators(symbol, "1d", candles, ANALYSIS_INDICATORS)
        latest: dict[str, float] = {}
        for series in indicators.series:
            for point in reversed(series.points):
                if point.value is not None:
                    latest[series.key] = round(point.value, 4)
                    break

        try:
            news = await self._news.get_for_symbol(symbol, limit=6)
        except Exception as exc:  # noqa: BLE001 - news is best-effort context
            logger.warning("News context fetch failed for %s: %s", symbol, exc)
            news = []

        return {
            "symbol": symbol,
            "quote": quote.model_dump(mode="json") if quote else None,
            "latest_indicators": latest,
            "recent_news": [
                {"title": a.title, "summary": a.summary, "source": a.source}
                for a in news
            ],
        }

    # -- chat ---------------------------------------------------------------
    async def chat_stream(
        self, messages: list[ChatMessage], symbol: str | None = None
    ) -> AsyncIterator[str]:
        system = CHAT_SYSTEM
        if symbol:
            quote = await self._market.get_quote(symbol)
            if quote is not None:
                system += (
                    "\n\nThe user is currently looking at "
                    f"{quote.display_symbol} ({quote.name or ''}). Latest snapshot: "
                    + json.dumps(quote.model_dump(mode="json"), default=str)
                )
        payload = [{"role": m.role.value, "content": m.content} for m in messages]
        provider = self._provider()
        try:
            async for chunk in provider.stream(payload, system=system, max_tokens=2048):
                yield chunk
        finally:
            await provider.aclose()

    # -- news classification ------------------------------------------------
    async def classify_news(
        self, symbol: str | None = None, limit: int = 10
    ) -> list[NewsClassification]:
        if symbol:
            articles = await self._news.get_for_symbol(symbol, limit=limit)
        else:
            articles = self._news.list_recent(limit=limit)
        if not articles:
            return []

        items = [{"title": a.title, "summary": a.summary or ""} for a in articles]
        provider = self._provider()
        try:
            raw = await provider.complete(
                CLASSIFY_SYSTEM, build_classify_prompt(items), max_tokens=1500
            )
        finally:
            await provider.aclose()

        verdicts = _parse_json_array(raw)
        by_index = {int(v.get("index", i)): v for i, v in enumerate(verdicts)}
        out: list[NewsClassification] = []
        for i, article in enumerate(articles):
            v = by_index.get(i, {})
            out.append(
                NewsClassification(
                    id=article.id,
                    title=article.title,
                    url=article.url,
                    sentiment=_coerce_sentiment(v.get("sentiment")),
                    importance=_coerce_rating(v.get("importance")),
                    rationale=str(v.get("rationale", "")).strip(),
                )
            )
        return out

    # -- persistence --------------------------------------------------------
    def _persist(self, report: AnalysisReport) -> None:
        with session_scope() as s:
            s.add(
                AiReportRow(
                    symbol=report.symbol,
                    provider=report.provider,
                    model=report.model,
                    sentiment=report.sentiment.value,
                    payload=report.model_dump(mode="json"),
                    created_at=report.created_at or utcnow(),
                )
            )

    def latest_report(self, symbol: str) -> AnalysisReport | None:
        sym = self._market.normalize(symbol)
        with session_scope() as s:
            row = (
                s.execute(
                    select(AiReportRow)
                    .where(AiReportRow.symbol == sym)
                    .order_by(AiReportRow.created_at.desc(), AiReportRow.id.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            return AnalysisReport(**row.payload) if row else None


# ---------------------------------------------------------------------------
# Lenient parsing helpers (models occasionally wrap JSON in prose / fences)
# ---------------------------------------------------------------------------


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def _parse_json_object(text: str) -> dict[str, object]:
    cleaned = _strip_fences(text)
    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            value = json.loads(cleaned[start : end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
    logger.warning("Could not parse JSON object from model output.")
    return {"summary": text.strip()}


def _parse_json_array(text: str) -> list[dict[str, object]]:
    cleaned = _strip_fences(text)
    try:
        value = json.loads(cleaned)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start != -1 and end > start:
        try:
            value = json.loads(cleaned[start : end + 1])
            if isinstance(value, list):
                return [v for v in value if isinstance(v, dict)]
        except json.JSONDecodeError:
            pass
    logger.warning("Could not parse JSON array from model output.")
    return []


def _coerce_sentiment(value: object) -> Sentiment:
    try:
        return Sentiment(str(value).strip().lower())
    except ValueError:
        return Sentiment.NEUTRAL


def _coerce_rating(value: object) -> int:
    try:
        return max(1, min(5, int(round(float(value)))))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 3


def _str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []
