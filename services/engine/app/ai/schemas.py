"""AI domain models + API schemas (Phase 6).

These Pydantic shapes are mirrored in ``renderer/src/lib/contracts.ts``. The
analysis report and news classification are deliberately structured (rather than
free text) so the renderer can render them as rich, typed views and so they can
be persisted to the ``ai_reports`` table and reused by alerts later.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Sentiment(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str


# ---- Stock analysis --------------------------------------------------------


class AnalyzeRequest(BaseModel):
    symbol: str


class AnalysisReport(BaseModel):
    """A structured, model-generated stock report (also persisted)."""

    symbol: str
    provider: str
    model: str
    sentiment: Sentiment = Sentiment.NEUTRAL
    rating: int = Field(default=3, ge=1, le=5)  # 1 = strong sell … 5 = strong buy
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    technical_outlook: str = ""
    recommendation: str = ""
    disclaimer: str = "AI-generated analysis. Not financial advice."
    created_at: datetime | None = None


# ---- Chat ------------------------------------------------------------------


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    symbol: str | None = None  # optional symbol context to ground the answer


# ---- News classification ---------------------------------------------------


class ClassifyRequest(BaseModel):
    symbol: str | None = None  # classify this symbol's news; else recent market news
    limit: int = Field(default=10, ge=1, le=40)


class NewsClassification(BaseModel):
    id: int | None = None
    title: str
    url: str
    sentiment: Sentiment = Sentiment.NEUTRAL
    importance: int = Field(default=3, ge=1, le=5)
    rationale: str = ""


# ---- Status ----------------------------------------------------------------


class AIStatus(BaseModel):
    ready: bool  # an active provider is configured + usable
    active_provider: str
    model: str
    configured: dict[str, bool]  # provider -> has an API key (or keyless)
    providers: list[str]  # known AI providers


class ProviderSelection(BaseModel):
    """Set the active AI provider (and optionally a model override)."""

    active_provider: str
    model: str | None = None
