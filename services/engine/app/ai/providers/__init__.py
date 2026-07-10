"""Concrete AI provider adapters. Heavy SDKs are imported lazily inside each
adapter so only the active provider's dependency must be installed."""

from app.ai.providers.anthropic_adapter import AnthropicProvider
from app.ai.providers.gemini_adapter import GeminiProvider
from app.ai.providers.ollama_adapter import OllamaProvider
from app.ai.providers.openai_adapter import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
    "OpenAIProvider",
]
