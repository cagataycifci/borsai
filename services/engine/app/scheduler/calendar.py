"""Economic calendar: recurring macro events + known FOMC/CPI dates (Phase 8).

Pure, offline-friendly logic — no network required. Known high-impact dates are
listed explicitly; weekly releases (jobless claims, etc.) are generated relative
to *today* so the feed stays fresh without manual updates.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from app.scheduler.schemas import EconomicCalendar, EconomicEvent

# FOMC meeting announcement dates (US) — 2025–2026.
_FOMC_DATES: list[date] = [
    date(2025, 1, 29),
    date(2025, 3, 19),
    date(2025, 5, 7),
    date(2025, 6, 18),
    date(2025, 7, 30),
    date(2025, 9, 17),
    date(2025, 11, 5),
    date(2025, 12, 17),
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 11, 4),
    date(2026, 12, 16),
]

# US CPI release dates (approximate official schedule).
_CPI_DATES: list[date] = [
    date(2025, 1, 15),
    date(2025, 2, 12),
    date(2025, 3, 12),
    date(2025, 4, 10),
    date(2025, 5, 13),
    date(2025, 6, 11),
    date(2025, 7, 15),
    date(2025, 8, 12),
    date(2025, 9, 11),
    date(2025, 10, 15),
    date(2025, 11, 13),
    date(2025, 12, 10),
    date(2026, 1, 14),
    date(2026, 2, 11),
    date(2026, 3, 11),
    date(2026, 4, 14),
    date(2026, 5, 12),
    date(2026, 6, 10),
]


def _at(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(d, time(hour, minute), tzinfo=UTC)


def _second_tuesday(year: int, month: int) -> date:
    """Return the second Tuesday of a month (common release pattern)."""
    d = date(year, month, 1)
    while d.weekday() != 1:  # Tuesday
        d += timedelta(days=1)
    return d + timedelta(days=7)


def build_economic_calendar(days: int = 14) -> EconomicCalendar:
    """Build an upcoming economic calendar for the next *days* days."""
    today = datetime.now(UTC).date()
    end = today + timedelta(days=days)
    events: list[EconomicEvent] = []

    # Known FOMC decisions (14:00 ET ≈ 19:00 UTC in winter, 18:00 in summer — use 18:00).
    for d in _FOMC_DATES:
        if today <= d <= end:
            events.append(
                EconomicEvent(
                    title="FOMC Rate Decision & Statement",
                    country="US",
                    impact="high",
                    event_at=_at(d, 18, 0),
                    category="monetary_policy",
                )
            )

    # US CPI.
    for d in _CPI_DATES:
        if today <= d <= end:
            events.append(
                EconomicEvent(
                    title="US CPI (Consumer Price Index)",
                    country="US",
                    impact="high",
                    event_at=_at(d, 13, 30),
                    category="inflation",
                )
            )

    # US Non-Farm Payrolls — first Friday of each month.
    cursor = today.replace(day=1)
    while cursor <= end:
        first = cursor.replace(day=1)
        while first.weekday() != 4:  # Friday
            first += timedelta(days=1)
        if today <= first <= end:
            events.append(
                EconomicEvent(
                    title="US Non-Farm Payrolls",
                    country="US",
                    impact="high",
                    event_at=_at(first, 13, 30),
                    category="employment",
                )
            )
        # Advance to next month.
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    # Weekly US Initial Jobless Claims — every Thursday 13:30 UTC.
    d = today
    while d <= end:
        if d.weekday() == 3:  # Thursday
            events.append(
                EconomicEvent(
                    title="US Initial Jobless Claims",
                    country="US",
                    impact="medium",
                    event_at=_at(d, 13, 30),
                    category="employment",
                )
            )
        d += timedelta(days=1)

    # Turkey CPI — second Tuesday of each month, ~10:00 TR (07:00 UTC).
    for year in {today.year, end.year}:
        for month in range(1, 13):
            tue = _second_tuesday(year, month)
            if today <= tue <= end:
                events.append(
                    EconomicEvent(
                        title="Turkey CPI (TÜİK)",
                        country="TR",
                        impact="high",
                        event_at=_at(tue, 7, 0),
                        category="inflation",
                    )
                )

    # ECB rate decision — approximate known 2025–2026 dates.
    _ECB_DATES = [
        date(2025, 1, 30),
        date(2025, 3, 6),
        date(2025, 4, 17),
        date(2025, 6, 5),
        date(2025, 7, 24),
        date(2025, 9, 11),
        date(2025, 10, 30),
        date(2025, 12, 18),
        date(2026, 1, 29),
        date(2026, 3, 5),
        date(2026, 4, 16),
        date(2026, 6, 4),
    ]
    for d in _ECB_DATES:
        if today <= d <= end:
            events.append(
                EconomicEvent(
                    title="ECB Rate Decision",
                    country="EU",
                    impact="high",
                    event_at=_at(d, 13, 15),
                    category="monetary_policy",
                )
            )

    events.sort(key=lambda e: e.event_at)
    return EconomicCalendar(
        events=events,
        from_date=datetime.combine(today, time.min, tzinfo=UTC),
        to_date=datetime.combine(end, time.max, tzinfo=UTC),
    )
