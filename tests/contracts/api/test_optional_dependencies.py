from __future__ import annotations

import pytest

import fuggers_py.calc as calc
import fuggers_py.calc.scheduler as scheduler_module

from fuggers_py.calc.calc_graph import NodeId
from fuggers_py.calc.errors import SchedulerError


def test_calc_public_api_stays_importable_without_engine_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scheduler_module, "croniter", None)

    interval = calc.IntervalScheduler([NodeId("price:ABC")], interval_seconds=60.0)

    assert interval.interval_seconds == 60.0
    with pytest.raises(SchedulerError, match="croniter"):
        calc.CronScheduler([NodeId("curve:usd")], expression="0 * * * *")
