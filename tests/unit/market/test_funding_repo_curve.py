from __future__ import annotations

import math

import pytest

from fuggers_py._core import Date
from fuggers_py._curves_impl.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py._curves_impl.value_type import ValueType
from fuggers_py._curves_impl.funding import RepoCurve


def test_repo_curve_wraps_term_structure_and_provides_df_zero_and_forward() -> None:
    ref = Date.from_ymd(2025, 1, 1)
    rate = 0.05
    tenor_180d = 180 / 365
    tenor_360d = 360 / 365
    df_180d = math.exp(-rate * tenor_180d)
    df_360d = math.exp(-rate * tenor_360d)

    inner = DiscreteCurve(
        ref,
        tenors=[tenor_180d, tenor_360d],
        values=[df_180d, df_360d],
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LOG_LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    curve = RepoCurve(inner)
    start = ref.add_days(180)
    end = ref.add_days(360)

    assert float(curve.discount_factor(end)) == pytest.approx(df_360d, abs=1e-12)
    assert float(curve.zero_rate(end)) == pytest.approx(rate, abs=1e-12)
    assert float(curve.forward_rate(start, end)) == pytest.approx((df_180d / df_360d - 1.0) / 0.5, abs=1e-12)
    assert curve.reference_date == ref
