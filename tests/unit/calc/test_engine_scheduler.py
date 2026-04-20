from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import fuggers_py._calc.scheduler as scheduler_module

import pytest

from fuggers_py._calc.calc_graph import NodeId
from fuggers_py._calc.errors import SchedulerError
from fuggers_py._calc.scheduler import CronScheduler, EodScheduler, IntervalScheduler, ThrottleManager, UpdateSource


class _FakeCroniter:
    def __init__(self, expression: str, start_time: datetime) -> None:
        if expression != "0 * * * *":
            raise ValueError(f"Invalid cron expression: {expression}")
        self.start_time = start_time

    def get_next(self, result_type: type[datetime]) -> datetime:
        if result_type is not datetime:
            raise AssertionError("CronScheduler should request datetime ticks from croniter.")
        next_hour = self.start_time.replace(minute=0, second=0, microsecond=0)
        if self.start_time >= next_hour:
            next_hour += timedelta(hours=1)
        return next_hour


@pytest.mark.asyncio
async def test_interval_scheduler_publishes_updates_via_queue() -> None:
    scheduler = IntervalScheduler([NodeId("price:ABC")], interval_seconds=60.0)
    queue = scheduler.subscribe()

    updates = await scheduler.tick(now=datetime(2026, 3, 14, 9, 0, tzinfo=UTC))
    queued = await queue.get()

    assert updates[0].node_id == NodeId("price:ABC")
    assert updates[0].source is UpdateSource.INTERVAL
    assert queued == updates[0]


@pytest.mark.asyncio
async def test_eod_scheduler_runs_once_per_day() -> None:
    scheduler = EodScheduler([NodeId("nav:portfolio")], run_time=time(17, 0), check_interval_seconds=60.0)

    assert await scheduler.tick(now=datetime(2026, 3, 14, 16, 59, tzinfo=UTC)) == ()
    first = await scheduler.tick(now=datetime(2026, 3, 14, 17, 0, tzinfo=UTC))
    second = await scheduler.tick(now=datetime(2026, 3, 14, 17, 1, tzinfo=UTC))
    third = await scheduler.tick(now=datetime(2026, 3, 15, 17, 0, tzinfo=UTC))

    assert len(first) == 1
    assert first[0].source is UpdateSource.EOD
    assert second == ()
    assert len(third) == 1


def test_cron_scheduler_accepts_valid_five_field_expression(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler_module, "croniter", _FakeCroniter)

    scheduler = CronScheduler([NodeId("curve:usd")], expression="0 * * * *")

    assert scheduler.expression == "0 * * * *"


def test_cron_scheduler_rejects_invalid_expression_with_scheduler_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler_module, "croniter", _FakeCroniter)

    with pytest.raises(SchedulerError, match="Invalid cron expression"):
        CronScheduler([NodeId("curve:usd")], expression="not a cron")


def test_cron_scheduler_requires_optional_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler_module, "croniter", None)

    with pytest.raises(SchedulerError, match="croniter"):
        CronScheduler([NodeId("curve:usd")], expression="0 * * * *")


def test_cron_scheduler_rejects_empty_expression() -> None:
    with pytest.raises(SchedulerError, match="non-empty cron expression"):
        CronScheduler([NodeId("curve:usd")], expression="   ")


@pytest.mark.asyncio
async def test_cron_scheduler_ticks_for_valid_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler_module, "croniter", _FakeCroniter)
    scheduler = CronScheduler([NodeId("curve:usd")], expression="0 * * * *")

    assert await scheduler.tick(now=datetime(2026, 3, 14, 9, 30, tzinfo=UTC)) == ()
    assert await scheduler.tick(now=datetime(2026, 3, 14, 9, 59, tzinfo=UTC)) == ()

    updates = await scheduler.tick(now=datetime(2026, 3, 14, 10, 0, tzinfo=UTC))

    assert len(updates) == 1
    assert updates[0].node_id == NodeId("curve:usd")
    assert updates[0].source is UpdateSource.CRON
    assert updates[0].detail == "0 * * * *"
    assert updates[0].timestamp == datetime(2026, 3, 14, 10, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_cron_scheduler_advances_without_duplicate_firing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler_module, "croniter", _FakeCroniter)
    scheduler = CronScheduler([NodeId("curve:usd")], expression="0 * * * *")

    assert await scheduler.tick(now=datetime(2026, 3, 14, 9, 15, tzinfo=UTC)) == ()
    first = await scheduler.tick(now=datetime(2026, 3, 14, 10, 0, tzinfo=UTC))
    assert await scheduler.tick(now=datetime(2026, 3, 14, 10, 30, tzinfo=UTC)) == ()
    second = await scheduler.tick(now=datetime(2026, 3, 14, 11, 0, tzinfo=UTC))

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].timestamp == datetime(2026, 3, 14, 10, 0, tzinfo=UTC)
    assert second[0].timestamp == datetime(2026, 3, 14, 11, 0, tzinfo=UTC)


def test_throttle_manager_is_deterministic() -> None:
    throttle = ThrottleManager(min_interval_seconds=10.0)
    now = datetime(2026, 3, 14, 9, 0, tzinfo=UTC)

    assert throttle.allow("quote:ABC", now=now) is True
    assert throttle.allow("quote:ABC", now=now) is False
    assert throttle.remaining("quote:ABC", now=now) == 10.0
    assert throttle.allow("quote:ABC", now=datetime(2026, 3, 14, 9, 0, 11, tzinfo=UTC)) is True


def test_throttle_manager_reset_all_clears_remaining_time() -> None:
    throttle = ThrottleManager(min_interval_seconds=10.0)
    now = datetime(2026, 3, 14, 9, 0, tzinfo=UTC)

    assert throttle.allow("curve:usd", now=now) is True
    assert throttle.remaining("curve:usd", now=datetime(2026, 3, 14, 9, 0, 5, tzinfo=UTC)) == 5.0
    throttle.reset()
    assert throttle.remaining("curve:usd", now=datetime(2026, 3, 14, 9, 0, 5, tzinfo=UTC)) == 0.0
