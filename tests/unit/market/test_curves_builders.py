from __future__ import annotations

import math
from decimal import Decimal

import pytest

from fuggers_py._core.types import Date
from fuggers_py._curves_impl import (
    DiscountCurveBuilder,
    ExtrapolationMethod,
    InterpolationMethod,
    ZeroCurveBuilder,
)
from fuggers_py._curves_impl.errors import MixedPillarTypes


def test_discount_curve_builder_default_interpolation_df_is_log_linear() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = (
        DiscountCurveBuilder(reference_date=ref)
        .add_pillar(1.0, math.exp(-0.05 * 1.0))
        .add_pillar(2.0, math.exp(-0.05 * 2.0))
        .build()
    )
    assert curve.interpolation_method() is InterpolationMethod.LOG_LINEAR


def test_discount_curve_builder_default_interpolation_zero_is_linear() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = DiscountCurveBuilder(reference_date=ref).add_zero_rate(1.0, 0.05).add_zero_rate(2.0, 0.05).build()
    assert curve.interpolation_method() is InterpolationMethod.LINEAR


def test_discount_curve_builder_rejects_mixed_pillars() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    builder = DiscountCurveBuilder(reference_date=ref).add_pillar(1.0, 0.95)
    with pytest.raises(MixedPillarTypes):
        builder.add_zero_rate(2.0, 0.02)


def test_zero_curve_builder_df_at_one_year_constant_rate() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = (
        ZeroCurveBuilder(reference_date=ref)
        .with_interpolation(InterpolationMethod.LINEAR)
        .with_extrapolation(ExtrapolationMethod.FLAT_FORWARD)
        .add_rate(ref.add_days(365), Decimal("0.05"))
        .add_rate(ref.add_days(365 * 2), Decimal("0.05"))
        .build()
    )

    df_1y = curve.discount_factor(ref.add_days(365))
    assert float(df_1y) == pytest.approx(math.exp(-0.05), abs=1e-12)
