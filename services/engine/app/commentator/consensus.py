"""Pure consensus logic for attributed opinions (Phase 9)."""

from __future__ import annotations

from app.ai.schemas import Sentiment
from app.commentator.schemas import AttributedOpinion, ConsensusLabel


def compute_consensus(opinions: list[AttributedOpinion]) -> tuple[ConsensusLabel, float, bool]:
    """Return (consensus label, agreement score 0–1, disagreement flag)."""
    if not opinions:
        return ConsensusLabel.NEUTRAL, 0.0, False

    weights = {"bullish": 0, "bearish": 0, "neutral": 0}
    for op in opinions:
        weights[op.sentiment.value] += op.importance

    total = sum(weights.values()) or 1
    shares = {k: v / total for k, v in weights.items()}
    dominant = max(shares, key=shares.get)
    agreement = shares[dominant]

    # Mixed when no side exceeds 50% or top two are close.
    sorted_shares = sorted(shares.values(), reverse=True)
    disagreement = len(sorted_shares) > 1 and (sorted_shares[0] - sorted_shares[1]) < 0.15

    if disagreement:
        label = ConsensusLabel.MIXED
    elif dominant == "bullish":
        label = ConsensusLabel.BULLISH
    elif dominant == "bearish":
        label = ConsensusLabel.BEARISH
    else:
        label = ConsensusLabel.NEUTRAL

    return label, round(agreement, 2), disagreement


def build_summary(
    symbol: str,
    consensus: ConsensusLabel,
    opinions: list[AttributedOpinion],
    disagreement: bool,
) -> str:
    n = len(opinions)
    if n == 0:
        return f"No recent attributed commentary found for {symbol}."

    bulls = sum(1 for o in opinions if o.sentiment == Sentiment.BULLISH)
    bears = sum(1 for o in opinions if o.sentiment == Sentiment.BEARISH)
    parts = [f"{n} headline{'s' if n != 1 else ''} analyzed"]
    parts.append(f"consensus: {consensus.value}")
    if disagreement:
        parts.append("sources disagree")
    else:
        parts.append(f"({bulls} bullish, {bears} bearish)")
    return "; ".join(parts) + "."
