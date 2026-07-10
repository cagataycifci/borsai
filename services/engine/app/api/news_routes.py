"""News API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.news import NewsArticle, NewsService

from .deps import get_news_service

router = APIRouter(prefix="/api/v1/news", tags=["news"])

NewsDep = Annotated[NewsService, Depends(get_news_service)]


@router.get("", response_model=list[NewsArticle], summary="Recent aggregated news")
async def list_news(
    service: NewsDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NewsArticle]:
    """Return stored articles, newest first. On an empty store (first run) this
    triggers a one-time refresh so the feed isn't empty."""
    if offset == 0 and service.count() == 0:
        await service.refresh()
    return service.list_recent(limit=limit, offset=offset)


@router.post("/refresh", summary="Fetch + store fresh articles from all sources")
async def refresh_news(service: NewsDep) -> dict[str, int]:
    stored = await service.refresh()
    return {"stored": stored}


@router.get(
    "/{symbol}", response_model=list[NewsArticle], summary="News for one symbol"
)
async def news_for_symbol(
    service: NewsDep,
    symbol: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[NewsArticle]:
    return await service.get_for_symbol(symbol, limit=limit)
