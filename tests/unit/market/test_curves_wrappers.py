from __future__ import annotations

import math

import pytest

from fuggers_py._core.types import Date
from fuggers_py._curves_impl.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py._curves_impl.errors import InvalidCurveInput
from fuggers_py._curves_impl.value_type import ValueType


def test_term_structure_from_discount_factors_df_zero_forward() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    r = 0.05
    tenors = [1.0, 2.0]
    dfs = [math.exp(-r * t) for t in tenors]

    inner = DiscreteCurve(
        ref,
        tenors=tenors,
        values=dfs,
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LOG_LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    curve = inner

    df_1y = curve.discount_factor(ref.add_days(365))
    assert float(df_1y) == pytest.approx(math.exp(-0.05), abs=1e-12)

    z_1y = curve.zero_rate(ref.add_days(365))
    assert float(z_1y.value()) == pytest.approx(0.05, abs=1e-12)

    fwd_1y_2y = curve.forward_rate_at_tenors(1.0, 2.0)
    assert fwd_1y_2y == pytest.approx(0.05, abs=1e-12)

    with pytest.raises(ValueError):
        _ = curve.forward_rate_at_tenors(2.0, 1.0)


def test_term_structure_from_zero_rates_discount_factor() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    r = 0.05
    inner = DiscreteCurve(
        ref,
        tenors=[1.0, 2.0],
        values=[r, r],
        value_type=ValueType.continuous_zero(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    curve = inner
    assert float(curve.discount_factor(ref.add_days(365))) == pytest.approx(math.exp(-0.05), abs=1e-12)
