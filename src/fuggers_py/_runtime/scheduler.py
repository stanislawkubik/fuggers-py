"""Async scheduler helpers for reactive engine orchestration.

Schedulers emit :class:`NodeUpdate` events at deterministic timestamps so the
reactive engine can process interval, end-of-day, and cron-style triggers
without guessing when a batch was produced. The schedulers here are fanout
helpers, not durable job runners.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date as native_date
from datetime import datetime, time as native_time
from enum import Enum
from typing import Iterable

from .calc_graph import NodeId
from .errors import SchedulerError

try:  # pragma: no cover - optional dependency
    from croniter import croniter
except Exception:  # pragma: no cover - optional dependency
    croniter = None

_CRON_VALIDATION_BASE = datetime(2000, 1, 1, tzinfo=UTC)


def _now() -> datetime:
    return datetime.now(UTC)


def _next_cron_run(expression: str, base: datetime) -> datetime:
    if croniter is None:  # pragma: no cover - optional dependency
        raise SchedulerError("CronScheduler requires the optional 'croniter' dependency.")
    try:
        return croniter(expression, base).get_next(datetime)
    except Exception as exc:
        raise SchedulerError(f"Invalid cron expression: {expression!r}.") from exc


class UpdateSource(str, Enum):
    """Origin of a node update entering the reactive engine."""

    INTERVAL = "INTERVAL"
    EOD = "EOD"
    CRON = "CRON"
    MARKET_DATA = "MARKET_DATA"
    MANUAL = "MANUAL"
    GRAPH = "GRAPH"


@dataclass(frozen=True, slots=True)
class NodeUpdate:
    """Timestamped node update emitted by a scheduler or market-data path.

    The payload is left generic so the reactive layer can carry scheduler,
    market-data, or graph-update objects through the same queue.
    """

    node_id: NodeId
    source: UpdateSource
    timestamp: datetime = field(default_factory=_now)
    payload: object | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        """Normalize the node identifier."""
        object.__setattr__(self, "node_id", NodeId.parse(self.node_id))


class _AsyncFanout:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def _publish(self, item: object) -> None:
        for queue in tuple(self._subscribers):
            queue.put_nowait(item)


class ThrottleManager:
    """Simple per-key throttle used to suppress rapid repeated updates.

    Each key tracks the last accepted timestamp so repeated market-data bursts
    can be rate-limited without dropping unrelated keys.
    """

    def __init__(self, min_interval_seconds: float) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be non-negative.")
        self.min_interval_seconds = float(min_interval_seconds)
        self._last_seen: dict[str, datetime] = {}

    def allow(self, key: str, *, now: datetime | None = None) -> bool:
        """Return ``True`` when an update is outside the throttle window."""
        current = now or _now()
        previous = self._last_seen.get(key)
        if previous is not None:
            elapsed = (current - previous).total_seconds()
            if elapsed < self.min_interval_seconds:
                return False
        self._last_seen[key] = current
        return True

    def remaining(self, key: str, *, now: datetime | None = None) -> float:
        """Return the remaining throttle window in seconds."""
        current = now or _now()
        previous = self._last_seen.get(key)
        if previous is None:
            return 0.0
        elapsed = (current - previous).total_seconds()
        return max(0.0, self.min_interval_seconds - elapsed)

    def reset(self, key: str | None = None) -> None:
        """Reset the throttle state for one key or for all keys."""
        if key is None:
            self._last_seen.clear()
            return
        self._last_seen.pop(key, None)


class _BaseScheduler(_AsyncFanout):
    def __init__(self, node_ids: Iterable[NodeId | str]) -> None:
        super().__init__()
        self.node_ids = tuple(NodeId.parse(node_id) for node_id in node_ids)
        self._task: asyncio.Task | None = None

    async def _emit(
        self,
        source: UpdateSource,
        *,
        timestamp: datetime | None = None,
        payload: object | None = None,
        detail: str | None = None,
    ) -> tuple[NodeUpdate, ...]:
        """Emit one update per registered node using a shared timestamp."""
        event_timestamp = timestamp or _now()
        updates = tuple(
            NodeUpdate(
                node_id=node_id,
                source=source,
                timestamp=event_timestamp,
                payload=payload,
                detail=detail,
            )
            for node_id in self.node_ids
        )
        for update in updates:
            await self._publish(update)
        return updates

    async def start(self) -> None:
        """Start the scheduler background loop if it is not already running."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name=f"{type(self).__name__}.run")

    async def stop(self) -> None:
        """Stop the scheduler background loop and clear its task handle."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def tick(self, now: datetime | None = None) -> tuple[NodeUpdate, ...]:
        """Run a single scheduler evaluation step."""
        raise NotImplementedError

    async def _run(self) -> None:
        """Background loop implemented by concrete scheduler types."""
        raise NotImplementedError


class IntervalScheduler(_BaseScheduler):
    """Emit updates on a fixed cadence."""

    def __init__(self, node_ids: Iterable[NodeId | str], *, interval_seconds: float, immediate: bool = False) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive.")
        super().__init__(node_ids)
        self.interval_seconds = float(interval_seconds)
        self.immediate = immediate

    async def tick(self, now: datetime | None = None) -> tuple[NodeUpdate, ...]:
        """Emit an interval update immediately when ticked."""
        return await self._emit(UpdateSource.INTERVAL, timestamp=now)

    async def _run(self) -> None:
        """Sleep for the configured interval between emitted ticks."""
        if self.immediate:
            await self.tick()
        while True:
            await asyncio.sleep(self.interval_seconds)
            await self.tick()


class EodScheduler(_BaseScheduler):
    """Emit once per date after the configured end-of-day time."""

    def __init__(
        self,
        node_ids: Iterable[NodeId | str],
        *,
        run_time: native_time | None = None,
        check_interval_seconds: float = 60.0,
    ) -> None:
        super().__init__(node_ids)
        self.run_time = run_time or native_time(hour=17, minute=0)
        if check_interval_seconds <= 0:
            raise ValueError("check_interval_seconds must be positive.")
        self.check_interval_seconds = float(check_interval_seconds)
        self._last_run_date: native_date | None = None

    def due(self, now: datetime) -> bool:
        """Return ``True`` when the scheduler should emit for ``now``."""
        if self._last_run_date == now.date():
            return False
        return (now.hour, now.minute, now.second) >= (self.run_time.hour, self.run_time.minute, self.run_time.second)

    async def tick(self, now: datetime | None = None) -> tuple[NodeUpdate, ...]:
        """Emit an EOD update once the configured time has been reached."""
        current = now or _now()
        if not self.due(current):
            return ()
        self._last_run_date = current.date()
        return await self._emit(UpdateSource.EOD, timestamp=current)

    async def _run(self) -> None:
        """Poll the clock at the configured cadence."""
        while True:
            await asyncio.sleep(self.check_interval_seconds)
            await self.tick()


class CronScheduler(_BaseScheduler):
    """Emit updates when a cron expression becomes due."""

    def __init__(
        self,
        node_ids: Iterable[NodeId | str],
        *,
        expression: str,
        check_interval_seconds: float = 30.0,
    ) -> None:
        super().__init__(node_ids)
        self.expression = expression.strip()
        if not self.expression:
            raise SchedulerError("CronScheduler requires a non-empty cron expression.")
        if check_interval_seconds <= 0:
            raise ValueError("check_interval_seconds must be positive.")
        self.check_interval_seconds = float(check_interval_seconds)
        self._next_run: datetime | None = None
        _next_cron_run(self.expression, _CRON_VALIDATION_BASE)

    def _compute_next_run(self, now: datetime) -> datetime:
        """Return the next run after ``now``."""
        return _next_cron_run(self.expression, now)

    async def tick(self, now: datetime | None = None) -> tuple[NodeUpdate, ...]:
        """Emit a cron update when the next scheduled run has arrived."""
        current = now or _now()
        if self._next_run is None:
            self._next_run = self._compute_next_run(current)
            return ()
        if current < self._next_run:
            return ()
        updates = await self._emit(UpdateSource.CRON, timestamp=current, detail=self.expression)
        self._next_run = self._compute_next_run(current)
        return updates

    async def _run(self) -> None:
        """Poll the cron expression at the configured cadence."""
        while True:
            await asyncio.sleep(self.check_interval_seconds)
            await self.tick()


__all__ = [
    "CronScheduler",
    "EodScheduler",
    "IntervalScheduler",
    "NodeUpdate",
    "ThrottleManager",
    "UpdateSource",
]
