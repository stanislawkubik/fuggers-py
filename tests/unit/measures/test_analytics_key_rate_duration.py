from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._measures.pricing import BondPricer
from fuggers_py._measures.risk.duration import STANDARD_KEY_RATE_TENORS, key_rate_duration_at_tenor
from fuggers_py._products.bonds.instruments import FixedBond
from fuggers_py._core import Tenor
from fuggers_py._core.types import Compounding, Date, Frequency
from fuggers_py._curves_impl import ZeroCurveBuilder
from fuggers_py._curves_impl.bumping import ParallelBump


def _curve(ref: Date) -> object:
    return (
        ZeroCurveBuilder(reference_date=ref, compounding=Compounding.CONTINUOUS)
        .add_rate(ref.add_days(365), Decimal("0.02"))
        .add_rate(ref.add_days(365 * 5), Decimal("0.03"))
        .add_rate(ref.add_days(365 * 10), Decimal("0.035"))
        .add_rate(ref.add_days(365 * 30), Decimal("0.04"))
        .build()
    )


def _effective_duration_from_curve(bond: FixedBond, curve: object, settlement: Date, bump: float = 1e-4) -> Decimal:
    pricer = BondPricer()
    p0 = pricer.price_from_curve(bond, curve, settlement).dirty.as_percentage()
    p_up = pricer.price_from_curve(bond, ParallelBump(bump).apply(curve), settlement).dirty.as_percentage()
    p_dn = pricer.price_from_curve(bond, ParallelBump(-bump).apply(curve), settlement).dirty.as_percentage()
    return (p_dn - p_up) / (Decimal(2) * p0 * Decimal(str(bump)))


def test_key_rate_duration_positive_and_sensible() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    bond = FixedBond.new(
        issue_date=ref,
        maturity_date=ref.add_days(365 * 10),
        coupon_rate=Decimal("0.04"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    curve = _curve(ref)
    settlement = ref

    krd = key_rate_duration_at_tenor(
        bond,
        curve,
        settlement,
        tenor=Tenor.parse("5Y"),
        bump=1e-4,
    )
    assert krd > 0
    assert float(krd) < 50


def test_key_rate_sum_matches_effective_duration() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    bond = FixedBond.new(
        issue_date=ref,
        maturity_date=ref.add_days(365 * 10),
        coupon_rate=Decimal("0.04"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    curve = _curve(ref)

    effective = _effective_duration_from_curve(bond, curve, ref)

    durations = [
        key_rate_duration_at_tenor(bond, curve, ref, tenor=tenor, bump=1e-4, tenor_grid=STANDARD_KEY_RATE_TENORS)
        for tenor in STANDARD_KEY_RATE_TENORS
    ]
    total = sum(durations, Decimal(0))

    assert float(total) == pytest.approx(float(effective), rel=0.1)


def test_key_rate_peak_near_maturity_bucket() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    maturity = Tenor.parse("10Y")
    bond = FixedBond.new(
        issue_date=ref,
        maturity_date=maturity.add_to(ref),
        coupon_rate=Decimal("0.035"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    curve = _curve(ref)

    krd_values = {
        tenor: key_rate_duration_at_tenor(bond, curve, ref, tenor=tenor, bump=1e-4)
        for tenor in STANDARD_KEY_RATE_TENORS
    }
    max_tenor = max(krd_values, key=lambda t: krd_values[t])

    maturity_years = maturity.to_years_approx()
    closest = min(STANDARD_KEY_RATE_TENORS, key=lambda t: abs(t.to_years_approx() - maturity_years))

    assert max_tenor == closest
