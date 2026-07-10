"""Prompt construction for the AI layer.

Kept separate from the service so the wording is easy to tune and unit-test. The
analysis and classification prompts request a strict JSON object/array so the
service can parse the model output into typed schemas.
"""

from __future__ import annotations

import json

ANALYSIS_SYSTEM = (
    "You are a sober, risk-aware equity analyst for a market terminal. You are "
    "given a context bundle (latest quote, key technical indicators, and recent "
    "news headlines) for one ticker. Produce a concise, balanced analysis. Never "
    "give personalized financial advice; frame everything as informational. "
    "Respond with ONLY a single JSON object, no markdown fences, matching this "
    "shape:\n"
    "{\n"
    '  "sentiment": "bullish" | "bearish" | "neutral",\n'
    '  "rating": 1-5 (1=strong sell, 3=hold, 5=strong buy),\n'
    '  "summary": "2-3 sentence overview",\n'
    '  "key_points": ["short bullet", ...],\n'
    '  "risks": ["short bullet", ...],\n'
    '  "technical_outlook": "1-2 sentences on the indicator picture",\n'
    '  "recommendation": "1 sentence, informational not advice"\n'
    "}"
)

CHAT_SYSTEM = (
    "You are the AI assistant inside Borsa AI Terminal, a desktop market terminal "
    "covering Borsa Istanbul (BIST) and US markets. Be concise, accurate, and "
    "neutral. Explain reasoning briefly. You are not a licensed advisor: include a "
    "short reminder that this is informational, not financial advice, when the user "
    "asks what to buy/sell."
)

CLASSIFY_SYSTEM = (
    "You classify financial news headlines. For each numbered item you are given, "
    "judge its likely market impact. Respond with ONLY a JSON array, no markdown "
    "fences, one object per input item in the same order, each matching:\n"
    "{\n"
    '  "index": <the item number>,\n'
    '  "sentiment": "bullish" | "bearish" | "neutral",\n'
    '  "importance": 1-5 (1=noise, 5=highly market-moving),\n'
    '  "rationale": "short reason"\n'
    "}"
)


def build_analysis_prompt(context: dict[str, object]) -> str:
    """Render the assembled context bundle into the analysis user prompt."""
    return (
        "Analyze the following ticker using this context bundle:\n\n"
        + json.dumps(context, indent=2, default=str)
        + "\n\nReturn the JSON object now."
    )


def build_classify_prompt(items: list[dict[str, str]]) -> str:
    """Render numbered headlines for classification."""
    lines = [
        f"{i}. {it['title']}" + (f" — {it['summary']}" if it.get("summary") else "")
        for i, it in enumerate(items)
    ]
    return "Classify these headlines:\n\n" + "\n".join(lines) + "\n\nReturn the JSON array now."
