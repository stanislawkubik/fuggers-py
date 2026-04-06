from __future__ import annotations

from fuggers_py.calc import CronScheduler, IntervalScheduler, NodeId, SchedulerError


def main() -> None:
    interval = IntervalScheduler([NodeId("price:ABC")], interval_seconds=60.0)
    assert interval.interval_seconds == 60.0

    try:
        CronScheduler([NodeId("curve:usd")], expression="0 * * * *")
    except SchedulerError as exc:
        message = str(exc)
        if "croniter" not in message:
            raise AssertionError(message) from exc
    else:
        raise AssertionError("CronScheduler unexpectedly worked without the engine extra.")


if __name__ == "__main__":
    main()
