from __future__ import annotations

from decimal import Decimal
from dataclasses import dataclass

import pytest

from fuggers_py.rates import IndexConventions, IndexFixingStore, ObservationShiftType, OvernightCompounding
from fuggers_py._core import Date
from fuggers_py._core.calendars import WeekendCalendar


def _flat_store(rate: str = "0.05") -> IndexFixingStore:
    store = IndexFixingStore()
    start = Date.from_ymd(2024, 1, 1)
    for offset in range(0, 15):
        store.add_fixing("SOFR", start.add_days(offset), Decimal(rate))
    return store


@dataclass(frozen=True, slots=True)
class _ReferenceDateForwardCurve:
    reference_date: Date
    rate: Decimal = Decimal("0.05")

    def forward_rate_at(self, tenor: float) -> Decimal:
        return self.rate


def test_compounded_in_arrears_flat_rate() -> None:
    store = _flat_store()
    conventions = IndexConventions(overnight_compounding=OvernightCompounding.COMPOUNDED)
    rate = OvernightCompounding.COMPOUNDED.compounded_rate(
        Date.from_ymd(2024, 1, 2),
        Date.from_ymd(2024, 1, 9),
        index_name="SOFR",
        fixing_store=store,
        conventions=conventions,
        calendar=WeekendCalendar(),
    )
    assert Decimal("0.049") < rate < Decimal("0.051")


def test_simple_average_flat_rate() -> None:
    store = _flat_store()
    conventions = IndexConventions(overnight_compounding=OvernightCompounding.SIMPLE)
    rate = OvernightCompounding.SIMPLE.simple_average_rate(
        Date.from_ymd(2024, 1, 2),
        Date.from_ymd(2024, 1, 9),
        index_name="SOFR",
        fixing_store=store,
        conventions=conventions,
        calendar=WeekendCalendar(),
    )
    assert float(rate) == pytest.approx(0.05)


def test_required_fixing_dates() -> None:
    conventions = IndexConventions(overnight_compounding=OvernightCompounding.COMPOUNDED)
    dates = OvernightCompounding.COMPOUNDED.required_fixing_dates(
        Date.from_ymd(2024, 1, 5),
        Date.from_ymd(2024, 1, 10),
        conventions=conventions,
        calendar=WeekendCalendar(),
    )
    assert dates[0] == Date.from_ymd(2024, 1, 5)
    assert dates[-1] == Date.from_ymd(2024, 1, 9)


def test_accrual_factor() -> None:
    conventions = IndexConventions()
    accrual = OvernightCompounding.COMPOUNDED.accrual_factor(
        Date.from_ymd(2024, 1, 2),
        Date.from_ymd(2024, 1, 12),
        conventions=conventions,
    )
    assert accrual > Decimal("0.02")


def test_compounded_rate_with_lookback_and_lockout() -> None:
    store = _flat_store()
    conventions = IndexConventions(
        overnight_compounding=OvernightCompounding.COMPOUNDED,
        shift_type=ObservationShiftType.LOOKBACK,
        lookback_days=2,
        lockout_days=1,
    )
    rate = OvernightCompounding.COMPOUNDED.compounded_rate(
        Date.from_ymd(2024, 1, 8),
        Date.from_ymd(2024, 1, 15),
        index_name="SOFR",
        fixing_store=store,
        conventions=conventions,
        calendar=WeekendCalendar(),
    )
    assert Decimal("0.049") < rate < Decimal("0.051")


def test_required_fixing_dates_respect_business_calendar() -> None:
    conventions = IndexConventions(overnight_compounding=OvernightCompounding.COMPOUNDED)
    dates = OvernightCompounding.COMPOUNDED.required_fixing_dates(
        Date.from_ymd(2024, 1, 5),
        Date.from_ymd(2024, 1, 10),
        conventions=conventions,
        calendar=WeekendCalendar(),
    )
    assert Date.from_ymd(2024, 1, 6) not in dates
    assert Date.from_ymd(2024, 1, 7) not in dates


def test_simple_average_rate_accepts_reference_date_forward_curve() -> None:
    conventions = IndexConventions(overnight_compounding=OvernightCompounding.SIMPLE)
    rate = OvernightCompounding.SIMPLE.simple_average_rate(
        Date.from_ymd(2024, 1, 2),
        Date.from_ymd(2024, 1, 9),
        index_name="SOFR",
        fixing_store=IndexFixingStore(),
        conventions=conventions,
        calendar=WeekendCalendar(),
        forward_curve=_ReferenceDateForwardCurve(Date.from_ymd(2024, 1, 2)),
        as_of=Date.from_ymd(2024, 1, 1),
    )

    assert float(rate) == pytest.approx(0.05)
