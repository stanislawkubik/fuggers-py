from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.products.bonds.instruments import FixedBondBuilder
from fuggers_py.core import Compounding, Date, Frequency, Yield


def test_fixed_bond_accrued_interest_basic() -> None:
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2025, 1, 1))
        .with_coupon_rate(Decimal("0.06"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .build()
    )
    # Half way through the first coupon period: accrued should be half the coupon.
    accrued = bond.accrued_interest(Date.from_ymd(2024, 4, 1))
    assert accrued == Decimal("1.5")

    assert bond.accrued_interest(Date.from_ymd(2024, 1, 1)) == Decimal(0)
    assert bond.accrued_interest(Date.from_ymd(2024, 7, 1)) == Decimal(0)


def test_price_yield_round_trip_simple_fixed_bond() -> None:
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2026, 1, 1))
        .with_coupon_rate(Decimal("0.05"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .build()
    )

    settlement = Date.from_ymd(2024, 1, 1)
    ytm = Yield.new(Decimal("0.05"), Compounding.SEMI_ANNUAL)

    price = bond.price_from_yield(ytm, settlement)
    ytm2 = bond.yield_from_price(price.clean, settlement)

    assert float(price.clean.as_percentage()) == pytest.approx(100.0, abs=1e-10)
    assert float(ytm2.ytm.value()) == pytest.approx(0.05, abs=1e-12)
