from __future__ import annotations

from fuggers_py.products.bonds.cashflows import Schedule, ScheduleConfig
from fuggers_py.reference.bonds.types import CalendarId, StubPeriodRules
from fuggers_py.core.types import Date, Frequency


def test_schedule_generation_backward_semi_annual() -> None:
    cfg = ScheduleConfig(
        start_date=Date.from_ymd(2024, 1, 1),
        end_date=Date.from_ymd(2025, 1, 1),
        frequency=Frequency.SEMI_ANNUAL,
        calendar=CalendarId.weekend_only(),
    )
    schedule = Schedule.generate(cfg)
    assert schedule.unadjusted_dates == [
        Date.from_ymd(2024, 1, 1),
        Date.from_ymd(2024, 7, 1),
        Date.from_ymd(2025, 1, 1),
    ]
    assert schedule.dates == schedule.unadjusted_dates


def test_schedule_end_of_month_rule_backward() -> None:
    cfg = ScheduleConfig(
        start_date=Date.from_ymd(2024, 1, 31),
        end_date=Date.from_ymd(2024, 4, 30),
        frequency=Frequency.MONTHLY,
        calendar=CalendarId.weekend_only(),
        end_of_month=True,
    )
    schedule = Schedule.generate(cfg)
    assert schedule.unadjusted_dates == [
        Date.from_ymd(2024, 1, 31),
        Date.from_ymd(2024, 2, 29),
        Date.from_ymd(2024, 3, 31),
        Date.from_ymd(2024, 4, 30),
    ]


def test_schedule_front_stub_uses_first_regular_date_forward() -> None:
    stub_rules = StubPeriodRules(first_regular_date=Date.from_ymd(2024, 2, 15))
    cfg = ScheduleConfig(
        start_date=Date.from_ymd(2024, 1, 15),
        end_date=Date.from_ymd(2024, 10, 15),
        frequency=Frequency.QUARTERLY,
        calendar=CalendarId.weekend_only(),
        stub_rules=stub_rules,
    )
    schedule = Schedule.generate(cfg)
    assert schedule.unadjusted_dates == [
        Date.from_ymd(2024, 1, 15),
        Date.from_ymd(2024, 2, 15),
        Date.from_ymd(2024, 5, 15),
        Date.from_ymd(2024, 8, 15),
        Date.from_ymd(2024, 10, 15),
    ]

