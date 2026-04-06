from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.pricers.bonds import TipsPricer
from fuggers_py.products.bonds import TipsBond
from fuggers_py.core import Compounding, Currency, Date, Frequency, Yield
from fuggers_py.core import YearMonth
from fuggers_py.market.snapshot import InflationFixing
from fuggers_py.market.sources import InMemoryInflationFixingSource
from fuggers_py.reference.inflation import USD_CPI_U_NSA


def _fixing(month: str, value: str) -> InflationFixing:
    return InflationFixing(
        index_name="CPURNSA",
        observation_month=YearMonth.parse(month),
        value=Decimal(value),
    )


def _source() -> InMemoryInflationFixingSource:
    return InMemoryInflationFixingSource(
        [
            _fixing("2023-10", "100"),
            _fixing("2023-11", "100"),
            _fixing("2024-01", "101"),
            _fixing("2024-02", "102"),
            _fixing("2024-04", "104"),
            _fixing("2024-05", "104"),
            _fixing("2024-10", "108"),
            _fixing("2024-11", "108"),
            _fixing("2025-04", "112"),
            _fixing("2025-05", "112"),
            _fixing("2025-10", "116"),
            _fixing("2025-11", "116"),
        ]
    )


def _bond() -> TipsBond:
    return TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        dated_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2026, 1, 15),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        base_reference_date=Date.from_ymd(2024, 1, 15),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
    )


def test_tips_real_yield_risk_metrics_are_positive_and_sensible() -> None:
    bond = _bond()
    source = _source()
    pricer = TipsPricer()
    settlement = Date.from_ymd(2024, 4, 15)
    real_yield = Yield.new(Decimal("0.015"), Compounding.SEMI_ANNUAL)

    metrics = pricer.risk_metrics_from_real_yield(
        bond,
        real_yield,
        settlement,
        fixing_source=source,
    )

    assert metrics.modified_duration > 0
    assert metrics.macaulay_duration > metrics.modified_duration
    assert metrics.dv01 > 0
    assert metrics.convexity > 0


def test_tips_price_moves_inverse_to_real_yield_and_dv01_is_consistent() -> None:
    bond = _bond()
    source = _source()
    pricer = TipsPricer()
    settlement = Date.from_ymd(2024, 4, 15)
    base_yield = Yield.new(Decimal("0.015"), Compounding.SEMI_ANNUAL)
    lower_yield = Yield.new(Decimal("0.0149"), Compounding.SEMI_ANNUAL)
    higher_yield = Yield.new(Decimal("0.0151"), Compounding.SEMI_ANNUAL)

    dirty_down = pricer.dirty_price_from_real_yield(
        bond,
        lower_yield,
        settlement,
        fixing_source=source,
    ).as_percentage()
    dirty_base = pricer.dirty_price_from_real_yield(
        bond,
        base_yield,
        settlement,
        fixing_source=source,
    ).as_percentage()
    dirty_up = pricer.dirty_price_from_real_yield(
        bond,
        higher_yield,
        settlement,
        fixing_source=source,
    ).as_percentage()
    metrics = pricer.risk_metrics_from_real_yield(
        bond,
        base_yield,
        settlement,
        fixing_source=source,
    )

    assert dirty_down > dirty_base > dirty_up
    assert float(metrics.dv01) == pytest.approx(float((dirty_down - dirty_up) / Decimal(2)), rel=5e-3)
