"""AI layer (Phase 6): provider abstraction, factory, and service.

Mirrors the data layer — a thin :class:`AIProvider` protocol with concrete
adapters (Anthropic/OpenAI/Gemini/Ollama), a config-driven factory, and an
:class:`AIService` that assembles market context and prompts the active model.
"""

from app.ai.base import AIProvider, ProviderError
from app.ai.factory import build_ai_provider
from app.ai.schemas import (
    AIStatus,
    AnalysisReport,
    AnalyzeRequest,
    ChatMessage,
    ChatRequest,
    ClassifyRequest,
    NewsClassification,
    Sentiment,
)
from app.ai.service import AIService

__all__ = [
    "AIProvider",
    "AIService",
    "AIStatus",
    "AnalysisReport",
    "AnalyzeRequest",
    "ChatMessage",
    "ChatRequest",
    "ClassifyRequest",
    "NewsClassification",
    "ProviderError",
    "Sentiment",
    "build_ai_provider",
]
