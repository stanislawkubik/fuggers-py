from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fuggers_py.calc import CronScheduler, NodeId, UpdateSource


async def _main() -> None:
    scheduler = CronScheduler([NodeId("curve:usd")], expression="0 * * * *")

    first = await scheduler.tick(now=datetime(2026, 3, 15, 9, 30, tzinfo=UTC))
    second = await scheduler.tick(now=datetime(2026, 3, 15, 10, 0, tzinfo=UTC))

    assert first == ()
    assert len(second) == 1
    assert second[0].node_id == NodeId("curve:usd")
    assert second[0].source is UpdateSource.CRON
    assert second[0].detail == "0 * * * *"


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
