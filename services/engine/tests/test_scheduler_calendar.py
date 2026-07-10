"""Unit tests for the economic calendar builder."""

from __future__ import annotations

from app.scheduler.calendar import build_economic_calendar


def test_economic_calendar_returns_sorted_future_events() -> None:
    cal = build_economic_calendar(days=30)
    assert cal.from_date <= cal.to_date
    assert len(cal.events) >= 1
    # All events should fall within the window.
    for ev in cal.events:
        assert cal.from_date.date() <= ev.event_at.date() <= cal.to_date.date()
    # Sorted ascending by time.
    times = [e.event_at for e in cal.events]
    assert times == sorted(times)


def test_economic_calendar_includes_us_and_tr_events() -> None:
    cal = build_economic_calendar(days=60)
    countries = {e.country for e in cal.events}
    assert "US" in countries
    assert "TR" in countries
