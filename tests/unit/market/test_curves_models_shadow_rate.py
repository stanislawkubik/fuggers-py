from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.market.curves import DiscountCurveBuilder, ShadowRateCurve


def _base_curve():
    reference_date = Date.from_ymd(2026, 1, 1)
    curve = (
        DiscountCurveBuilder(reference_date=reference_date)
        .add_zero_rate(1.0, Decimal("-0.0200"))
        .add_zero_rate(5.0, Decimal("0.0100"))
        .build()
    )
    return reference_date, curve


def test_shadow_rate_curve_applies_a_smooth_lower_bound_to_negative_base_rates() -> None:
    reference_date, base_curve = _base_curve()
    shadow_curve = ShadowRateCurve(
        base_curve=base_curve,
        lower_bound=Decimal("-0.0050"),
        smoothing=Decimal("0.0010"),
    )

    one_year = reference_date.add_days(365)
    model_point = shadow_curve.model_point(one_year)

    assert model_point.base_zero_rate == Decimal("-0.0200")
    assert model_point.adjusted_zero_rate >= Decimal("-0.0050")
    assert model_point.adjustment > Decimal(0)
    assert shadow_curve.discount_factor(one_year) < base_curve.discount_factor(one_year)


def test_shadow_rate_curve_leaves_positive_rates_effectively_unchanged() -> None:
    reference_date, base_curve = _base_curve()
    shadow_curve = ShadowRateCurve(
        base_curve=base_curve,
        lower_bound=Decimal("-0.0050"),
        smoothing=Decimal("0.0010"),
    )

    five_year = reference_date.add_days(365 * 5)
    base_zero = base_curve.zero_rate(five_year).value()
    adjusted_zero = shadow_curve.zero_rate(five_year).value()

    assert float(adjusted_zero) == pytest.approx(float(base_zero), abs=1e-6)
    assert float(shadow_curve.discount_factor(five_year)) == pytest.approx(
        float(base_curve.discount_factor(five_year)),
        abs=1e-6,
    )
