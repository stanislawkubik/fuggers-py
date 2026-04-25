from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from fuggers_py._core import Compounding, Date, WeekendCalendar
from fuggers_py._core.daycounts import (
    Act360,
    Act365Fixed,
    Act365Leap,
    ActActAfb,
    ActActIsda,
    Thirty360E,
    Thirty360EIsda,
    Thirty360German,
    Thirty360US,
)
from fuggers_py.curves.conversion import ValueConverter
from fuggers_py.portfolio import Portfolio
from fuggers_py.portfolio.analytics import PortfolioAnalytics
from fuggers_py.portfolio.contribution import (
    contribution_by_rating,
    contribution_by_sector,
    dv01_contributions,
    spread_contributions,
)

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


LIGHT_PROPERTY_SETTINGS = settings(
    max_examples=12,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

COMPOUNDINGS = (
    Compounding.CONTINUOUS,
    Compounding.SIMPLE,
    Compounding.ANNUAL,
    Compounding.SEMI_ANNUAL,
    Compounding.QUARTERLY,
    Compounding.MONTHLY,
    Compounding.DAILY,
)
PORTFOLIO_SCALES = st.tuples(
    st.integers(min_value=1, max_value=400),
    st.integers(min_value=1, max_value=400),
    st.integers(min_value=1, max_value=400),
)


def _scaled_portfolio(ref: Date, scales: tuple[int, int, int]) -> Portfolio:
    base = make_portfolio(ref)
    positions = [
        replace(position, quantity=Decimal(str(scale)))
        for position, scale in zip(base.positions, scales, strict=True)
    ]
    return Portfolio.new(positions, currency=base.currency)


@LIGHT_PROPERTY_SETTINGS
@given(
    start_offset=st.integers(min_value=0, max_value=2500),
    span=st.integers(min_value=-720, max_value=720).filter(lambda value: value != 0),
)
def test_day_count_conventions_are_antisymmetric(start_offset: int, span: int) -> None:
    base = Date.from_ymd(2000, 1, 1)
    start = base.add_days(start_offset)
    end = start.add_days(span)
    conventions = (
        Act360(),
        Act365Fixed(),
        Act365Leap(),
        ActActAfb(),
        ActActIsda(),
        Thirty360E(),
        Thirty360EIsda(),
        Thirty360German(),
        Thirty360US(),
    )

    for convention in conventions:
        assert convention.day_count(start, end) == -convention.day_count(end, start)
        assert float(convention.year_fraction(start, end)) == pytest.approx(
            float(-convention.year_fraction(end, start)),
            abs=1e-12,
        )


@LIGHT_PROPERTY_SETTINGS
@given(
    rate=st.floats(min_value=0.0001, max_value=0.15, allow_nan=False, allow_infinity=False),
    tenor=st.floats(min_value=0.1, max_value=20.0, allow_nan=False, allow_infinity=False),
    compounding=st.sampled_from(COMPOUNDINGS),
)
def test_zero_discount_round_trip_is_stable(rate: float, tenor: float, compounding: Compounding) -> None:
    discount_factor = ValueConverter.zero_to_df(rate, tenor, compounding)
    recovered = ValueConverter.df_to_zero(discount_factor, tenor, compounding)

    assert recovered == pytest.approx(rate, abs=1e-10)


@LIGHT_PROPERTY_SETTINGS
@given(
    start_offset=st.integers(min_value=0, max_value=600),
    business_days=st.integers(min_value=-15, max_value=15),
)
def test_weekend_calendar_addition_inverts_business_day_counts(start_offset: int, business_days: int) -> None:
    calendar = WeekendCalendar()
    base = Date.from_ymd(2024, 1, 1)
    start = calendar.next_business_day(base.add_days(start_offset))
    result = calendar.add_business_days(start, business_days)

    assert calendar.business_days_between(start, result) == business_days
    assert calendar.is_business_day(result) is True


@LIGHT_PROPERTY_SETTINGS
@given(
    scales=PORTFOLIO_SCALES,
    metric=st.sampled_from(["duration", "dv01", "spread"]),
)
def test_grouped_contribution_maps_conserve_totals(scales: tuple[int, int, int], metric: str) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = _scaled_portfolio(ref, scales)
    curve = make_curve(ref)
    positions = PortfolioAnalytics(portfolio).position_metrics(curve, ref)
    expected_total = {
        "duration": sum((item.duration for item in positions), Decimal(0)),
        "dv01": dv01_contributions(portfolio, curve=curve, settlement_date=ref).total,
        "spread": spread_contributions(portfolio, curve=curve, settlement_date=ref).total,
    }[metric]

    sector_total = sum(
        contribution_by_sector(portfolio, curve=curve, settlement_date=ref, metric=metric).values(),
        Decimal(0),
    )
    rating_total = sum(
        contribution_by_rating(portfolio, curve=curve, settlement_date=ref, metric=metric).values(),
        Decimal(0),
    )

    assert float(sector_total) == pytest.approx(float(expected_total))
    assert float(rating_total) == pytest.approx(float(expected_total))
