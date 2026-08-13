"""Unit tests for morning summary template builder."""

from __future__ import annotations

from app.scheduler.schemas import QuoteSnapshot, ReportRegion
from app.scheduler.summary import _template_overview


def test_template_overview_with_movers() -> None:
    benchmarks = [
        QuoteSnapshot(
            symbol="SPY",
            display_symbol="SPY",
            change_percent=1.5,
            price=500.0,
        ),
        QuoteSnapshot(
            symbol="QQQ",
            display_symbol="QQQ",
            change_percent=-0.8,
            price=400.0,
        ),
    ]
    overview, highlights = _template_overview(ReportRegion.US, benchmarks)
    assert "SPY" in overview
    assert len(highlights) >= 1


def test_template_overview_empty() -> None:
    overview, highlights = _template_overview(ReportRegion.GLOBAL, [])
    assert "No benchmark data" in overview
    assert highlights == []
