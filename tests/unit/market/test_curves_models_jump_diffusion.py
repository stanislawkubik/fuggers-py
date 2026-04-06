from __future__ import annotations

from decimal import Decimal
from math import exp

import pytest

from fuggers_py.core import Date
from fuggers_py.market.curves import DiscountCurveBuilder, JumpDiffusionCurve


def _flat_curve(rate: Decimal = Decimal("0.0300")):
    reference_date = Date.from_ymd(2026, 1, 1)
    curve = (
        DiscountCurveBuilder(reference_date=reference_date)
        .add_zero_rate(1.0, rate)
        .add_zero_rate(10.0, rate)
        .build()
    )
    return reference_date, curve


def test_jump_diffusion_curve_returns_explicit_adjustment_components() -> None:
    reference_date, base_curve = _flat_curve()
    curve = JumpDiffusionCurve(
        base_curve=base_curve,
        diffusion_volatility=Decimal("0.10"),
        jump_intensity=Decimal("0.20"),
        mean_jump_size=Decimal("-0.05"),
        jump_volatility=Decimal("0.15"),
        risk_premium_adjustment=Decimal("0.0010"),
    )

    components = curve.adjustment_components(Decimal("5.0"))
    expected_diffusion = Decimal("0.5") * Decimal("0.10") * Decimal("0.10") * Decimal("5.0")
    expected_jump = Decimal(str(0.20 * (exp(-0.05 + 0.5 * 0.15 * 0.15) - 1.0)))

    assert float(components.diffusion_adjustment) == pytest.approx(float(expected_diffusion), abs=1e-12)
    assert float(components.jump_adjustment) == pytest.approx(float(expected_jump), abs=1e-12)
    assert components.total_adjustment == components.diffusion_adjustment + components.jump_adjustment + Decimal("0.0010")

    five_year = reference_date.add_days(365 * 5)
    assert curve.zero_rate(five_year).value() == base_curve.zero_rate(five_year).value() + components.total_adjustment
    assert curve.discount_factor(five_year) < base_curve.discount_factor(five_year)


def test_jump_diffusion_curve_with_zero_inputs_reduces_to_the_base_curve() -> None:
    reference_date, base_curve = _flat_curve()
    curve = JumpDiffusionCurve(base_curve=base_curve)
    seven_year = reference_date.add_days(365 * 7)

    assert curve.adjustment_components(Decimal("7.0")).total_adjustment == Decimal(0)
    assert curve.zero_rate(seven_year).value() == base_curve.zero_rate(seven_year).value()
    assert curve.discount_factor(seven_year) == base_curve.discount_factor(seven_year)
