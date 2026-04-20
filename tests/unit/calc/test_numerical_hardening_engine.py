from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fuggers_py._core import Date
from fuggers_py._calc import NodeId, PricingEngineBuilder
from fuggers_py._calc.scheduler import IntervalScheduler
from fuggers_py._market.sources import MarketDataProvider
from fuggers_py._reference import ReferenceDataProvider


@pytest.mark.asyncio
async def test_interval_scheduler_uses_one_timestamp_per_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    import fuggers_py._calc.scheduler as scheduler_module

    now = datetime(2026, 3, 14, 9, 0, tzinfo=UTC)
    monkeypatch.setattr(scheduler_module, "_now", lambda: now)

    scheduler = IntervalScheduler([NodeId("price:A"), NodeId("price:B")], interval_seconds=60.0)
    updates = await scheduler.tick()

    assert updates[0].timestamp == now
    assert updates[1].timestamp == now


@pytest.mark.asyncio
async def test_reactive_engine_stop_cleans_subscriptions_and_allows_restart() -> None:
    engine = (
        PricingEngineBuilder.new()
        .with_market_data_provider(MarketDataProvider())
        .with_reference_data_provider(ReferenceDataProvider())
        .with_settlement_date(Date.from_ymd(2026, 3, 14))
        .with_default_interval_scheduler([NodeId("price:ABC")], interval_seconds=60.0)
        .build()
    )
    assert engine.reactive_engine is not None
    reactive = engine.reactive_engine
    scheduler = reactive.schedulers[0]

    await reactive.start()
    assert len(reactive.market_data_publisher._subscribers) == 1
    assert len(scheduler._subscribers) == 1

    await reactive.stop()
    assert len(reactive.market_data_publisher._subscribers) == 0
    assert len(scheduler._subscribers) == 0
    assert reactive._incoming_queue is None

    await reactive.start()
    assert len(reactive.market_data_publisher._subscribers) == 1
    assert len(scheduler._subscribers) == 1

    await reactive.stop()
