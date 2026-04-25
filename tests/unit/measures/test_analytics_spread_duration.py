from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.analytics_pricing import BondPricer
from fuggers_py.bonds.risk import modified_duration, spread_duration
from fuggers_py.bonds.instruments import FixedBond
from fuggers_py._core.types import Date, Frequency
from tests.helpers._rates_helpers import flat_curve


def _flat_curve(ref: Date, rate: str) -> object:
    return flat_curve(ref, rate)


def test_spread_duration_positive_and_close_to_modified() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _flat_curve(ref, "0.04")
    bond = FixedBond.new(
        issue_date=ref,
        maturity_date=ref.add_days(365 * 5),
        coupon_rate=Decimal("0.045"),
        frequency=Frequency.SEMI_ANNUAL,
    )

    pricer = BondPricer()
    price = pricer.price_from_curve(bond, curve, ref)
    ytm = pricer.yield_to_maturity(bond, price.clean, ref)

    sd = spread_duration(bond, ytm, ref, curve=curve, spread=Decimal("0.0"))
    md = modified_duration(bond, ytm, ref)

    assert sd > 0
    assert float(sd) == pytest.approx(float(md), rel=0.1)


def test_spread_duration_bump_symmetry() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _flat_curve(ref, "0.03")
    bond = FixedBond.new(
        issue_date=ref,
        maturity_date=ref.add_days(365 * 7),
        coupon_rate=Decimal("0.035"),
        frequency=Frequency.SEMI_ANNUAL,
    )

    pricer = BondPricer()
    price = pricer.price_from_curve(bond, curve, ref)
    ytm = pricer.yield_to_maturity(bond, price.clean, ref)

    sd_small = spread_duration(bond, ytm, ref, curve=curve, spread=Decimal("0.0"), bump=1e-4)
    sd_large = spread_duration(bond, ytm, ref, curve=curve, spread=Decimal("0.0"), bump=2e-4)

    assert float(sd_small) == pytest.approx(float(sd_large), rel=0.05)
