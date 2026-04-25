from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.instruments import FixedBondBuilder
from fuggers_py.bonds import BondPricer
from fuggers_py.bonds.types import YieldConvention
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Compounding, Date, Frequency, Yield


def test_yield_engine_round_trip_matches_example_treasury_bond() -> None:
    rules = YieldCalculationRules.us_treasury()
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2026, 1, 1))
        .with_coupon_rate(Decimal("0.05"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_rules(rules)
        .build()
    )

    settlement = Date.from_ymd(2024, 4, 1)
    assert bond.accrued_interest(settlement) == Decimal("1.25")

    pricer = BondPricer()
    ytm = Yield.new(Decimal("0.05"), Compounding.SEMI_ANNUAL)
    price = pricer.price_from_yield(bond, ytm, settlement)
    ytm2 = pricer.yield_from_price(bond, price.clean, settlement)

    assert float(ytm2.ytm.value()) == pytest.approx(0.05, abs=1e-10)
    assert ytm2.engine.convention is YieldConvention.STREET_CONVENTION


def test_yield_engine_recovers_higher_yield_after_bad_initial_guess() -> None:
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2026, 1, 1))
        .with_coupon_rate(Decimal("0.02"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_rules(YieldCalculationRules.us_treasury())
        .build()
    )

    settlement = Date.from_ymd(2024, 1, 1)
    pricer = BondPricer()

    ytm = Yield.new(Decimal("0.15"), Compounding.SEMI_ANNUAL)
    price = pricer.price_from_yield(bond, ytm, settlement)
    ytm2 = pricer.yield_from_price(bond, price.clean, settlement)

    assert float(ytm2.ytm.value()) == pytest.approx(0.15, abs=1e-9)

