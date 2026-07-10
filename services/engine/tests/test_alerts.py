"""Pure alert-engine tests + a monitor trigger/cooldown/broadcast test."""

from __future__ import annotations

from app.alerts.engine import Indicators, Snapshot, build_indicators
from app.alerts.engine import evaluate as evaluate_alert
from app.alerts.monitor import AlertMonitor
from app.alerts.schemas import Alert, AlertCreate, AlertType
from app.alerts.service import AlertService
from app.data.models import Candle, Quote


def _alert(atype: AlertType, threshold=None, **kw) -> Alert:
    return Alert(id=1, symbol="AAPL", type=atype, threshold=threshold, **kw)


def test_price_and_percent_conditions() -> None:
    assert evaluate_alert(
        _alert(AlertType.PRICE_ABOVE, 100), Snapshot(price=101)
    )
    assert evaluate_alert(_alert(AlertType.PRICE_ABOVE, 100), Snapshot(price=99)) is None
    assert evaluate_alert(_alert(AlertType.PRICE_BELOW, 100), Snapshot(price=99))
    assert evaluate_alert(
        _alert(AlertType.PERCENT_UP, 5), Snapshot(change_percent=6.2)
    )
    assert (
        evaluate_alert(_alert(AlertType.PERCENT_UP, 5), Snapshot(change_percent=3))
        is None
    )
    assert evaluate_alert(
        _alert(AlertType.PERCENT_DOWN, 5), Snapshot(change_percent=-7)
    )
    assert evaluate_alert(_alert(AlertType.VOLUME_ABOVE, 1000), Snapshot(volume=2000))


def test_rsi_and_cross_conditions() -> None:
    up = Snapshot(indicators=Indicators(rsi=75))
    assert evaluate_alert(_alert(AlertType.RSI_ABOVE, 70), up)
    assert evaluate_alert(_alert(AlertType.RSI_BELOW, 30), up) is None

    # MACD crosses above signal on the latest bar.
    macd_up = Snapshot(
        indicators=Indicators(macd_prev=-0.5, signal_prev=0.0, macd=0.2, signal=0.1)
    )
    assert evaluate_alert(_alert(AlertType.MACD_CROSS_UP), macd_up)
    assert evaluate_alert(_alert(AlertType.MACD_CROSS_DOWN), macd_up) is None

    # Golden cross: fast SMA moves from below to above the slow SMA.
    golden = Snapshot(
        indicators=Indicators(
            sma_fast_prev=9.0, sma_slow_prev=10.0, sma_fast=11.0, sma_slow=10.5
        )
    )
    assert evaluate_alert(_alert(AlertType.GOLDEN_CROSS), golden)
    assert evaluate_alert(_alert(AlertType.DEATH_CROSS), golden) is None
    # No cross when the ordering doesn't change.
    flat = Snapshot(
        indicators=Indicators(
            sma_fast_prev=11.0, sma_slow_prev=10.0, sma_fast=12.0, sma_slow=10.5
        )
    )
    assert evaluate_alert(_alert(AlertType.GOLDEN_CROSS), flat) is None


def test_build_indicators_from_candles() -> None:
    from datetime import UTC, datetime, timedelta

    base = datetime(2025, 1, 1, tzinfo=UTC)
    candles = [
        Candle(
            time=base + timedelta(days=i),
            open=100 + i,
            high=101 + i,
            low=99 + i,
            close=100 + i,
            volume=1000,
        )
        for i in range(260)
    ]
    ind = build_indicators(candles, fast=50, slow=200)
    # On a steady uptrend the fast SMA sits above the slow SMA and RSI is high.
    assert ind.rsi is not None and ind.rsi > 50
    assert ind.sma_fast is not None and ind.sma_slow is not None
    assert ind.sma_fast > ind.sma_slow


class _FakeMarket:
    async def get_quote(self, symbol: str) -> Quote:
        return Quote(
            symbol=symbol, display_symbol=symbol, price=150.0,
            change_percent=2.0, volume=5000,
        )

    async def get_history(self, symbol, interval, range_) -> list[Candle]:
        return []


class _FakeHub:
    def __init__(self) -> None:
        self.frames: list[dict] = []

    async def broadcast(self, frame: dict) -> None:
        self.frames.append(frame)


async def test_monitor_triggers_once_then_cooldown(initialized_db) -> None:
    service = AlertService()
    service.create(AlertCreate(symbol="AAPL", type=AlertType.PRICE_ABOVE, threshold=100))

    hub = _FakeHub()
    monitor = AlertMonitor(service, _FakeMarket(), hub)  # type: ignore[arg-type]

    await monitor._tick()
    assert len(hub.frames) == 1
    assert hub.frames[0]["type"] == "alert"
    assert hub.frames[0]["data"]["symbol"] == "AAPL"
    assert len(service.recent_events()) == 1

    # Cooldown (default 3600s) blocks a second immediate trigger.
    await monitor._tick()
    assert len(hub.frames) == 1
    assert len(service.recent_events()) == 1
