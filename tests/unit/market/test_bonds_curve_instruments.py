from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core.types import Compounding, Date, Frequency
from fuggers_py._curves_impl import ZeroCurveBuilder
from fuggers_py._curves_impl.bond_instruments import GovernmentCouponBond, GovernmentZeroCoupon


def _flat_curve(ref: Date, rate: str) -> object:
    return (
        ZeroCurveBuilder(reference_date=ref, compounding=Compounding.SEMI_ANNUAL)
        .add_rate(ref.add_days(365), Decimal(rate))
        .add_rate(ref.add_days(365 * 10), Decimal(rate))
        .build()
    )


def test_government_zero_coupon_quote_roundtrip() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _flat_curve(ref, "0.04")
    instr = GovernmentZeroCoupon(maturity=ref.add_days(365 * 2))

    price = instr.repriced_quote(curve, settlement_date=ref)
    target_df = instr.calibration_target_from_price(price)
    df = curve.discount_factor(instr.maturity)

    assert float(target_df) == pytest.approx(float(df), abs=1e-12)
    assert float(price) > 0


def test_government_coupon_bond_quote_roundtrip() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _flat_curve(ref, "0.03")
    instr = GovernmentCouponBond(
        maturity=ref.add_days(365 * 5),
        coupon_rate=Decimal("0.035"),
        frequency=Frequency.SEMI_ANNUAL,
    )

    price = instr.repriced_quote(curve, settlement_date=ref)
    target = instr.calibration_target_from_price(price)

    assert float(target) == pytest.approx(float(price), abs=1e-12)
    assert float(price) > 0
