"""AI API routes (Phase 6).

* ``GET  /api/v1/ai/status``       — active provider + readiness
* ``PUT  /api/v1/ai/provider``     — choose the active provider / model
* ``POST /api/v1/ai/analyze``      — structured stock-analysis report
* ``GET  /api/v1/ai/reports/{sym}``— most recent stored report for a symbol
* ``POST /api/v1/ai/classify``     — bullish/bearish/neutral + importance for news
* ``POST /api/v1/ai/chat``         — streaming chat (Server-Sent Events)

Chat streams as SSE: each token arrives as ``data: <json-string>`` and the stream
ends with ``data: [DONE]``; provider failures mid-stream arrive as an
``event: error`` frame.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.ai import (
    AIService,
    AIStatus,
    AnalysisReport,
    AnalyzeRequest,
    ChatRequest,
    ClassifyRequest,
    NewsClassification,
    ProviderError,
)
from app.ai.providers.gemini_adapter import resolve_gemini_model
from app.ai.schemas import ProviderSelection
from app.settings.service import AI_PROVIDERS, SettingsService

from .deps import get_ai_service, get_settings_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

AIDep = Annotated[AIService, Depends(get_ai_service)]
SettingsDep = Annotated[SettingsService, Depends(get_settings_service)]


@router.get("/status", response_model=AIStatus, summary="AI provider status")
def ai_status(service: AIDep) -> AIStatus:
    return service.status()


@router.put("/provider", response_model=AIStatus, summary="Select active AI provider")
def set_provider(
    service: AIDep, settings: SettingsDep, body: ProviderSelection
) -> AIStatus:
    if body.active_provider not in AI_PROVIDERS:
        raise HTTPException(
            status_code=400, detail=f"Unknown AI provider '{body.active_provider}'"
        )
    settings.set_active_ai_provider(body.active_provider)
    model = body.model
    if body.active_provider == "gemini" and model is not None:
        # Never persist the provider name or a retired Gemini id.
        model = resolve_gemini_model(model)
    settings.set_ai_model(model)
    return service.status()


@router.post("/analyze", response_model=AnalysisReport, summary="Analyze a stock")
async def analyze(service: AIDep, body: AnalyzeRequest) -> AnalysisReport:
    try:
        return await service.analyze(body.symbol)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/reports/{symbol}",
    response_model=AnalysisReport,
    summary="Most recent stored report",
)
def latest_report(service: AIDep, symbol: str) -> AnalysisReport:
    report = service.latest_report(symbol)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No report for '{symbol}'")
    return report


@router.post(
    "/classify",
    response_model=list[NewsClassification],
    summary="Classify recent news sentiment",
)
async def classify_news(
    service: AIDep, body: ClassifyRequest
) -> list[NewsClassification]:
    try:
        return await service.classify_news(body.symbol, body.limit)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/chat", summary="Streaming AI chat (SSE)")
async def chat(service: AIDep, body: ChatRequest) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        try:
            async for chunk in service.chat_stream(body.messages, body.symbol):
                yield f"data: {json.dumps(chunk)}\n\n"
        except ProviderError as exc:
            yield f"event: error\ndata: {json.dumps(str(exc))}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
