from __future__ import annotations

from fuggers_py._runtime import CronScheduler, IntervalScheduler, NodeId, SchedulerError


def main() -> None:
    interval = IntervalScheduler([NodeId("price:ABC")], interval_seconds=60.0)
    assert interval.interval_seconds == 60.0

    try:
        cron = CronScheduler([NodeId("curve:usd")], expression="0 * * * *")
    except SchedulerError as exc:
        message = str(exc)
        if "croniter" not in message:
            raise AssertionError(message) from exc
    else:
        assert cron.expression == "0 * * * *"


if __name__ == "__main__":
    main()
