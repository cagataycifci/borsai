"""Unit tests for commentator consensus logic."""

from __future__ import annotations

from app.ai.schemas import Sentiment
from app.commentator.consensus import build_summary, compute_consensus
from app.commentator.schemas import AttributedOpinion, ConsensusLabel


def _op(sentiment: Sentiment, importance: int = 3) -> AttributedOpinion:
    return AttributedOpinion(
        source="Test",
        title="Headline",
        url="https://ex.com/1",
        sentiment=sentiment,
        importance=importance,
        rationale="ok",
    )


def test_consensus_bullish_majority() -> None:
    opinions = [_op(Sentiment.BULLISH, 5), _op(Sentiment.BULLISH, 4), _op(Sentiment.NEUTRAL)]
    label, score, disagreement = compute_consensus(opinions)
    assert label == ConsensusLabel.BULLISH
    assert score > 0.5
    assert disagreement is False


def test_consensus_mixed_when_split() -> None:
    opinions = [
        _op(Sentiment.BULLISH, 3),
        _op(Sentiment.BEARISH, 3),
        _op(Sentiment.NEUTRAL, 2),
    ]
    label, _, disagreement = compute_consensus(opinions)
    assert label == ConsensusLabel.MIXED
    assert disagreement is True


def test_build_summary_mentions_disagreement() -> None:
    opinions = [_op(Sentiment.BULLISH), _op(Sentiment.BEARISH)]
    text = build_summary("AAPL", ConsensusLabel.MIXED, opinions, True)
    assert "disagree" in text
    assert "mixed" in text
