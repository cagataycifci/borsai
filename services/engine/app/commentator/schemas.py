"""Commentator schemas (Phase 9)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.ai.schemas import Sentiment


class ConsensusLabel(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class AttributedOpinion(BaseModel):
    source: str
    title: str
    url: str
    sentiment: Sentiment
    importance: int = Field(ge=1, le=5)
    rationale: str


class CommentatorReport(BaseModel):
    symbol: str
    consensus: ConsensusLabel
    agreement_score: float = Field(ge=0, le=1, description="1 = full agreement")
    disagreement: bool
    summary: str
    opinions: list[AttributedOpinion] = Field(default_factory=list)
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    generated_at: datetime
