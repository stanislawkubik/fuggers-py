from __future__ import annotations

import pytest

from fuggers_py.core.types import Date
from fuggers_py.market.curves.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py.market.curves.errors import InvalidCurveInput
from fuggers_py.market.curves.value_type import ValueType


def test_discrete_curve_creation_sorts_and_passes_through_points() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    tenors = [1.5, 0.5, 1.0]
    values = [0.97, 0.99, 0.98]

    curve = DiscreteCurve(
        ref,
        tenors=tenors,
        values=values,
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )

    assert curve.tenors().tolist() == pytest.approx([0.5, 1.0, 1.5])
    assert curve.values().tolist() == pytest.approx([0.99, 0.98, 0.97])
    for t, v in zip(curve.tenors(), curve.values(), strict=True):
        assert curve.value_at_tenor(float(t)) == pytest.approx(float(v))


def test_discrete_curve_linear_interpolation() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = DiscreteCurve(
        ref,
        tenors=[1.0, 2.0, 3.0],
        values=[0.01, 0.02, 0.03],
        value_type=ValueType.continuous_zero(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    assert curve.value_at_tenor(1.5) == pytest.approx(0.015)


def test_discrete_curve_flat_and_flat_forward_extrapolation() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    for method in (ExtrapolationMethod.FLAT, ExtrapolationMethod.FLAT_FORWARD):
        curve = DiscreteCurve(
            ref,
            tenors=[1.0, 2.0],
            values=[0.01, 0.02],
            value_type=ValueType.continuous_zero(),
            interpolation_method=InterpolationMethod.LINEAR,
            extrapolation_method=method,
        )
        assert curve.value_at_tenor(0.0) == pytest.approx(0.01)
        assert curve.value_at_tenor(3.0) == pytest.approx(0.02)


def test_discrete_curve_linear_extrapolation() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = DiscreteCurve(
        ref,
        tenors=[1.0, 2.0],
        values=[0.01, 0.02],
        value_type=ValueType.continuous_zero(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.LINEAR,
    )
    assert curve.value_at_tenor(0.0) == pytest.approx(0.0)
    assert curve.value_at_tenor(3.0) == pytest.approx(0.03)


def test_discrete_curve_derivative_out_of_range_is_none() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = DiscreteCurve(
        ref,
        tenors=[1.0, 2.0],
        values=[0.01, 0.02],
        value_type=ValueType.continuous_zero(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.LINEAR,
    )
    assert curve.derivative_at_tenor(1.5) == pytest.approx(0.01)
    assert curve.derivative_at_tenor(0.5) is None
    assert curve.derivative_at_tenor(2.5) is None


def test_discrete_curve_parametric_construction_errors() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    for method in (InterpolationMethod.NELSON_SIEGEL, InterpolationMethod.SVENSSON):
        with pytest.raises(InvalidCurveInput, match="Parametric models require calibration, not direct construction"):
            _ = DiscreteCurve(
                ref,
                tenors=[1.0, 2.0],
                values=[0.01, 0.02],
                value_type=ValueType.continuous_zero(),
                interpolation_method=method,
                extrapolation_method=ExtrapolationMethod.FLAT,
            )
