from __future__ import annotations

from math import exp

import pytest

from fuggers_py._core.types import Currency, Date
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.curves.errors import InvalidCurveInput, TenorOutOfBounds
from fuggers_py.curves.kernels.spline import CubicSplineKernel, ExponentialSplineKernel


def _nominal_spec(*, extrapolation_policy: str = "error") -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type="nominal",
        extrapolation_policy=extrapolation_policy,
    )


def test_substep_d7_exponential_spline_kernel_prices_through_yield_curve() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(),
        kernel=ExponentialSplineKernel(
            coefficients=[0.032, -0.008, 0.004],
            decay_factors=[0.40, 1.20],
            max_t=30.0,
        ),
    )

    expected_zero = 0.032 - 0.008 * exp(-0.40 * 5.0) + 0.004 * exp(-1.20 * 5.0)

    assert curve.rate_at(5.0) == pytest.approx(expected_zero)
    assert curve.discount_factor_at(5.0) == pytest.approx(exp(-expected_zero * 5.0))


def test_substep_d7_cubic_spline_kernel_matches_input_knots() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(),
        kernel=CubicSplineKernel(
            knot_tenors=[2.0, 4.0, 6.0, 8.0, 10.0],
            zero_rates=[0.024, 0.027, 0.031, 0.034, 0.036],
        ),
    )

    assert curve.rate_at(2.0) == pytest.approx(0.024)
    assert curve.rate_at(6.0) == pytest.approx(0.031)
    assert curve.rate_at(10.0) == pytest.approx(0.036)


def test_substep_d7_cubic_spline_kernel_supports_front_end_before_first_positive_knot() -> None:
    kernel = CubicSplineKernel(
        knot_tenors=[1.0, 3.0, 7.0],
        zero_rates=[-0.012, 0.006, 0.018],
    )

    assert kernel.rate_at(0.25) < 0.0
    assert kernel.discount_factor_at(0.25) > 1.0


def test_substep_d7_cubic_spline_kernel_is_continuous_around_interior_knot() -> None:
    kernel = CubicSplineKernel(
        knot_tenors=[2.0, 4.0, 6.0, 8.0, 10.0],
        zero_rates=[0.020, 0.023, 0.029, 0.032, 0.035],
    )
    epsilon = 1e-6

    left_value = kernel.rate_at(4.0 - epsilon)
    center_value = kernel.rate_at(4.0)
    right_value = kernel.rate_at(4.0 + epsilon)

    assert left_value == pytest.approx(center_value, abs=1e-6)
    assert right_value == pytest.approx(center_value, abs=1e-6)


def test_substep_d7_spline_kernels_support_extrapolation_when_enabled() -> None:
    cubic_kernel = CubicSplineKernel(
        knot_tenors=[2.0, 4.0, 6.0],
        zero_rates=[0.02, 0.025, 0.03],
        allow_extrapolation=True,
    )
    exponential_kernel = ExponentialSplineKernel(
        coefficients=[0.032, -0.008, 0.004],
        decay_factors=[0.40, 1.20],
        max_t=10.0,
        allow_extrapolation=True,
    )

    assert cubic_kernel.discount_factor_at(7.0) > 0.0
    assert exponential_kernel.rate_at(15.0) == pytest.approx(
        0.032 - 0.008 * exp(-0.40 * 15.0) + 0.004 * exp(-1.20 * 15.0)
    )


def test_substep_d7_error_policy_rejects_out_of_range_spline_curve_even_if_kernel_allows_it() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="error"),
        kernel=ExponentialSplineKernel(
            coefficients=[0.032, -0.008, 0.004],
            decay_factors=[0.40, 1.20],
            max_t=10.0,
            allow_extrapolation=True,
        ),
    )

    with pytest.raises(TenorOutOfBounds):
        curve.rate_at(15.0)


def test_substep_d7_hold_last_zero_rate_uses_final_cubic_spline_zero_rate() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="hold_last_zero_rate"),
        kernel=CubicSplineKernel(
            knot_tenors=[2.0, 4.0, 6.0],
            zero_rates=[0.02, 0.025, 0.03],
            allow_extrapolation=True,
        ),
    )

    assert curve.rate_at(8.0) == pytest.approx(0.03)
    assert curve.discount_factor_at(8.0) == pytest.approx(exp(-0.03 * 8.0))


def test_substep_d7_hold_last_native_rate_uses_exponential_spline_final_zero_rate() -> None:
    expected_final_zero = 0.032 - 0.008 * exp(-0.40 * 10.0) + 0.004 * exp(-1.20 * 10.0)
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="hold_last_native_rate"),
        kernel=ExponentialSplineKernel(
            coefficients=[0.032, -0.008, 0.004],
            decay_factors=[0.40, 1.20],
            max_t=10.0,
            allow_extrapolation=True,
        ),
    )

    assert curve.rate_at(15.0) == pytest.approx(expected_final_zero)


def test_substep_d7_hold_last_forward_rate_rejects_spline_kernel() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="hold_last_forward_rate"),
        kernel=CubicSplineKernel(
            knot_tenors=[2.0, 4.0, 6.0],
            zero_rates=[0.02, 0.025, 0.03],
            allow_extrapolation=True,
        ),
    )

    with pytest.raises(InvalidCurveInput, match="hold_last_forward_rate"):
        curve.rate_at(8.0)


def test_substep_d7_spline_kernels_reject_extrapolation_when_disabled() -> None:
    cubic_kernel = CubicSplineKernel(
        knot_tenors=[2.0, 4.0, 6.0],
        zero_rates=[0.02, 0.025, 0.03],
    )
    exponential_kernel = ExponentialSplineKernel(
        coefficients=[0.032, -0.008, 0.004],
        decay_factors=[0.40, 1.20],
        max_t=10.0,
    )

    with pytest.raises(TenorOutOfBounds):
        cubic_kernel.rate_at(7.0)
    with pytest.raises(TenorOutOfBounds):
        exponential_kernel.rate_at(15.0)


def test_substep_d7_spline_kernels_validate_inputs() -> None:
    with pytest.raises(InvalidCurveInput, match="len\\(decay_factors\\) \\+ 1"):
        ExponentialSplineKernel(
            coefficients=[0.03, -0.01],
            decay_factors=[0.40, 1.20],
            max_t=30.0,
        )

    with pytest.raises(InvalidCurveInput, match="decay_factors must be > 0"):
        ExponentialSplineKernel(
            coefficients=[0.032, -0.008, 0.004],
            decay_factors=[0.40, 0.0],
            max_t=30.0,
        )

    with pytest.raises(InvalidCurveInput, match="strictly increasing"):
        CubicSplineKernel(
            knot_tenors=[4.0, 2.0, 6.0],
            zero_rates=[0.02, 0.025, 0.03],
        )

    with pytest.raises(InvalidCurveInput, match="at least three spline knots"):
        CubicSplineKernel(
            knot_tenors=[2.0, 6.0],
            zero_rates=[0.02, 0.03],
        )
