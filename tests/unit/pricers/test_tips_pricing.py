from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._pricers.bonds import BondPricer, TipsPricer
from fuggers_py._products.bonds import TipsBond
from fuggers_py._core import Compounding, Currency, Date, Frequency, Price, Yield
from fuggers_py._core import YearMonth
from fuggers_py._market.snapshot import InflationFixing
from fuggers_py._market.sources import InMemoryInflationFixingSource
from fuggers_py._calc.pricing_router import PricingRouter
from fuggers_py.inflation import USD_CPI_U_NSA


def _fixing(month: str, value: str) -> InflationFixing:
    return InflationFixing(
        index_name="CPURNSA",
        observation_month=YearMonth.parse(month),
        value=Decimal(value),
    )


def _inflation_source() -> InMemoryInflationFixingSource:
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


def _deflation_source() -> InMemoryInflationFixingSource:
    return InMemoryInflationFixingSource(
        [
            _fixing("2023-10", "100"),
            _fixing("2023-11", "100"),
            _fixing("2024-04", "96"),
            _fixing("2024-05", "96"),
            _fixing("2024-10", "90"),
            _fixing("2024-11", "90"),
        ]
    )


def _tips(*, fixing_source: InMemoryInflationFixingSource | None = None) -> TipsBond:
    return TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        dated_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2026, 1, 15),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        base_reference_date=Date.from_ymd(2024, 1, 15),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
        fixing_source=fixing_source,
    )


def test_tips_clean_plus_accrued_equals_dirty_from_real_yield() -> None:
    bond = _tips()
    source = _inflation_source()
    pricer = TipsPricer()
    settlement = Date.from_ymd(2024, 4, 15)
    real_yield = Yield.new(Decimal("0.015"), Compounding.SEMI_ANNUAL)

    dirty = pricer.dirty_price_from_real_yield(
        bond,
        real_yield,
        settlement,
        fixing_source=source,
    )
    clean = pricer.clean_price_from_real_yield(
        bond,
        real_yield,
        settlement,
        fixing_source=source,
    )
    accrued = pricer.accrued_interest(bond, settlement, fixing_source=source)

    assert dirty.as_percentage() == clean.as_percentage() + accrued
    assert accrued > Decimal(0)


def test_tips_real_yield_price_roundtrip() -> None:
    bond = _tips()
    source = _inflation_source()
    pricer = TipsPricer()
    settlement = Date.from_ymd(2024, 4, 15)
    real_yield = Yield.new(Decimal("0.0175"), Compounding.SEMI_ANNUAL)

    clean_price = pricer.clean_price_from_real_yield(
        bond,
        real_yield,
        settlement,
        fixing_source=source,
    )
    solved = pricer.real_yield_from_clean_price(
        bond,
        clean_price,
        settlement,
        fixing_source=source,
    ).ytm

    assert float(solved.value()) == pytest.approx(float(real_yield.value()), abs=1e-10)


def test_generic_bond_pricer_dispatches_to_tips_pricer() -> None:
    bond = _tips()
    source = _inflation_source()
    settlement = Date.from_ymd(2024, 4, 15)
    real_yield = Yield.new(Decimal("0.0125"), Compounding.SEMI_ANNUAL)

    generic = BondPricer().price_from_yield(
        bond,
        real_yield,
        settlement,
        fixing_source=source,
    )
    dedicated = TipsPricer().price_from_real_yield(
        bond,
        real_yield,
        settlement,
        fixing_source=source,
    )

    assert generic.clean == dedicated.clean
    assert generic.dirty == dedicated.dirty
    assert generic.accrued == dedicated.accrued


def test_tips_pricing_respects_deflation_floor_at_maturity() -> None:
    bond = TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 1),
        dated_date=Date.from_ymd(2024, 1, 1),
        maturity_date=Date.from_ymd(2025, 1, 1),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        base_reference_date=Date.from_ymd(2024, 1, 1),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
    )
    source = _deflation_source()
    pricer = TipsPricer()
    settlement = Date.from_ymd(2024, 7, 1)
    zero_real_yield = Yield.new(Decimal("0.0"), Compounding.SEMI_ANNUAL)

    dirty = pricer.dirty_price_from_real_yield(
        bond,
        zero_real_yield,
        settlement,
        fixing_source=source,
    )
    future_flows = bond.projected_cash_flows(fixing_source=source, settlement_date=settlement)
    final_amount = sum((flow.factored_amount() for flow in future_flows), Decimal(0))

    assert final_amount == Decimal("100.9000")
    assert dirty.as_percentage() == Decimal("100.9000")


def test_tips_router_prices_market_clean_price_into_real_yield() -> None:
    bond = _tips()
    source = _inflation_source()
    router = PricingRouter()
    settlement = Date.from_ymd(2024, 4, 15)

    output = router.price(
        bond,
        settlement,
        market_price=Price.new(Decimal("102.00"), Currency.USD),
        market_data=source,
    )

    assert output.pricing_path == "tips_real_yield"
    assert output.clean_price == Decimal("102.00")
    assert output.dirty_price is not None and output.accrued_interest is not None
    assert output.dirty_price == output.clean_price + output.accrued_interest
    assert output.yield_to_maturity is not None
    assert output.modified_duration is not None and output.modified_duration > 0
