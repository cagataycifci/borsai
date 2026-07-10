"""Commentator service: news + AI classification → consensus (Phase 9)."""

from __future__ import annotations

from app.ai import AIService
from app.ai.schemas import NewsClassification, Sentiment
from app.commentator.consensus import build_summary, compute_consensus
from app.commentator.schemas import AttributedOpinion, CommentatorReport
from app.db.base import utcnow
from app.news.service import NewsService


class CommentatorService:
    def __init__(self, news: NewsService, ai: AIService) -> None:
        self._news = news
        self._ai = ai

    async def analyze(self, symbol: str, limit: int = 12) -> CommentatorReport:
        symbol = symbol.strip().upper()
        articles = await self._news.get_for_symbol(symbol, limit=limit)

        opinions: list[AttributedOpinion] = []
        if articles:
            try:
                verdicts = await self._ai.classify_news(symbol=symbol, limit=limit)
                opinions = _merge_opinions(articles, verdicts)
            except Exception:  # noqa: BLE001 — fall back to neutral template
                opinions = _neutral_opinions(articles)

        consensus, agreement, disagreement = compute_consensus(opinions)
        summary = build_summary(symbol, consensus, opinions, disagreement)

        return CommentatorReport(
            symbol=symbol,
            consensus=consensus,
            agreement_score=agreement,
            disagreement=disagreement,
            summary=summary,
            opinions=opinions,
            bullish_count=sum(1 for o in opinions if o.sentiment == Sentiment.BULLISH),
            bearish_count=sum(1 for o in opinions if o.sentiment == Sentiment.BEARISH),
            neutral_count=sum(1 for o in opinions if o.sentiment == Sentiment.NEUTRAL),
            generated_at=utcnow(),
        )


def _merge_opinions(articles, verdicts: list[NewsClassification]) -> list[AttributedOpinion]:
    by_url = {v.url: v for v in verdicts if v.url}
    out: list[AttributedOpinion] = []
    for art in articles:
        v = by_url.get(art.url)
        if v is None:
            continue
        out.append(
            AttributedOpinion(
                source=art.source,
                title=art.title,
                url=art.url,
                sentiment=v.sentiment,
                importance=v.importance,
                rationale=v.rationale,
            )
        )
    return out


def _neutral_opinions(articles) -> list[AttributedOpinion]:
    return [
        AttributedOpinion(
            source=a.source,
            title=a.title,
            url=a.url,
            sentiment=Sentiment.NEUTRAL,
            importance=2,
            rationale="Unclassified (AI unavailable)",
        )
        for a in articles[:8]
    ]
