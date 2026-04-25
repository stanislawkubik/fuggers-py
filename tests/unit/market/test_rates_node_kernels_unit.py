from __future__ import annotations

from math import exp, sqrt

import pytest

from fuggers_py._core.types import Currency, Date
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.curves.errors import InvalidCurveInput, TenorOutOfBounds
from fuggers_py.curves.kernels.nodes import (
    LinearZeroKernel,
    LogLinearDiscountKernel,
    MonotoneConvexKernel,
    PiecewiseConstantZeroKernel,
    PiecewiseFlatForwardKernel,
)


def _nominal_spec(*, extrapolation_policy: str = "error") -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type="nominal",
        extrapolation_policy=extrapolation_policy,
    )


def test_substep_d4_linear_zero_kernel_prices_through_yield_curve() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(),
        kernel=LinearZeroKernel(
            tenors=[1.0, 5.0],
            zero_rates=[0.03, 0.05],
        ),
    )

    assert curve.discount_factor_at(0.0) == pytest.approx(1.0)
    assert curve.rate_at(0.5) == pytest.approx(0.03)
    assert curve.rate_at(3.0) == pytest.approx(0.04)
    assert curve.discount_factor_at(3.0) == pytest.approx(exp(-0.04 * 3.0))


def test_substep_d4_log_linear_discount_kernel_preserves_discount_interpolation() -> None:
    df_1y = exp(-0.02 * 1.0)
    df_5y = exp(-0.04 * 5.0)
    curve = YieldCurve(
        spec=_nominal_spec(),
        kernel=LogLinearDiscountKernel(
            tenors=[1.0, 5.0],
            discount_factors=[df_1y, df_5y],
        ),
    )

    assert curve.discount_factor_at(1.0) == pytest.approx(df_1y)
    assert curve.discount_factor_at(3.0) == pytest.approx(sqrt(df_1y * df_5y))


def test_substep_d4_piecewise_constant_zero_kernel_holds_last_zero_rate_by_interval() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(),
        kernel=PiecewiseConstantZeroKernel(
            tenors=[1.0, 3.0, 5.0],
            zero_rates=[0.02, 0.03, 0.04],
        ),
    )

    assert curve.rate_at(0.5) == pytest.approx(0.02)
    assert curve.rate_at(2.5) == pytest.approx(0.02)
    assert curve.rate_at(3.0) == pytest.approx(0.03)


def test_substep_d4_piecewise_flat_forward_kernel_keeps_forward_flat_inside_interval() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(),
        kernel=PiecewiseFlatForwardKernel(
            tenors=[1.0, 3.0],
            zero_rates=[0.02, 0.03],
        ),
    )

    expected_forward = (0.03 * 3.0 - 0.02 * 1.0) / (3.0 - 1.0)

    assert curve.rate_at(2.0) == pytest.approx((0.02 * 1.0 + expected_forward * 1.0) / 2.0)
    assert curve.forward_rate_between(1.5, 2.5) == pytest.approx(expected_forward)


def test_substep_d4_monotone_convex_kernel_stays_pricing_usable() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(),
        kernel=MonotoneConvexKernel(
            tenors=[1.0, 3.0, 5.0],
            zero_rates=[0.02, 0.025, 0.03],
        ),
    )

    assert curve.rate_at(3.0) == pytest.approx(0.025)
    assert curve.discount_factor_at(2.0) > 0.0
    assert curve.forward_rate_between(1.5, 2.0) >= 0.0


def test_substep_d4_node_kernels_support_extrapolation_when_enabled() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="hold_last_native_rate"),
        kernel=LinearZeroKernel(
            tenors=[1.0, 5.0],
            zero_rates=[0.03, 0.05],
            allow_extrapolation=True,
        ),
    )

    assert curve.rate_at(6.0) == pytest.approx(0.05)
    assert curve.discount_factor_at(6.0) == pytest.approx(exp(-0.05 * 6.0))


def test_substep_d4_error_policy_rejects_out_of_range_public_curve_even_if_kernel_allows_it() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="error"),
        kernel=LinearZeroKernel(
            tenors=[1.0, 5.0],
            zero_rates=[0.03, 0.05],
            allow_extrapolation=True,
        ),
    )

    with pytest.raises(TenorOutOfBounds):
        curve.rate_at(6.0)


def test_substep_d4_hold_last_zero_rate_overrides_linear_zero_extrapolation() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="hold_last_zero_rate"),
        kernel=LinearZeroKernel(
            tenors=[1.0, 5.0],
            zero_rates=[0.03, 0.05],
            allow_extrapolation=True,
        ),
    )

    assert curve.rate_at(7.0) == pytest.approx(0.05)
    assert curve.discount_factor_at(7.0) == pytest.approx(exp(-0.05 * 7.0))


def test_substep_d4_hold_last_native_value_uses_discount_kernel_final_discount_factor() -> None:
    final_discount_factor = exp(-0.04 * 5.0)
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="hold_last_native_rate"),
        kernel=LogLinearDiscountKernel(
            tenors=[1.0, 5.0],
            discount_factors=[exp(-0.02 * 1.0), final_discount_factor],
            allow_extrapolation=True,
        ),
    )

    assert curve.discount_factor_at(7.0) == pytest.approx(final_discount_factor)
    assert curve.rate_at(7.0) == pytest.approx(0.04 * 5.0 / 7.0)


def test_substep_d4_hold_last_forward_rate_uses_flat_forward_tail() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="hold_last_forward_rate"),
        kernel=PiecewiseFlatForwardKernel(
            tenors=[1.0, 3.0],
            zero_rates=[0.02, 0.03],
            allow_extrapolation=True,
        ),
    )
    expected_forward = (0.03 * 3.0 - 0.02 * 1.0) / (3.0 - 1.0)
    expected_zero = (0.03 * 3.0 + expected_forward * (5.0 - 3.0)) / 5.0

    assert curve.rate_at(5.0) == pytest.approx(expected_zero)
    assert curve.discount_factor_at(5.0) == pytest.approx(exp(-expected_zero * 5.0))
    assert curve.forward_rate_between(4.0, 5.0) == pytest.approx(expected_forward)


def test_substep_d4_hold_last_forward_rate_rejects_node_kernel_without_clear_forward_tail() -> None:
    curve = YieldCurve(
        spec=_nominal_spec(extrapolation_policy="hold_last_forward_rate"),
        kernel=LinearZeroKernel(
            tenors=[1.0, 5.0],
            zero_rates=[0.03, 0.05],
            allow_extrapolation=True,
        ),
    )

    with pytest.raises(InvalidCurveInput, match="hold_last_forward_rate"):
        curve.rate_at(6.0)


def test_substep_d4_node_kernels_reject_extrapolation_when_disabled() -> None:
    kernel = LinearZeroKernel(
        tenors=[1.0, 5.0],
        zero_rates=[0.03, 0.05],
    )

    with pytest.raises(TenorOutOfBounds):
        kernel.discount_factor_at(6.0)


def test_substep_d4_log_linear_discount_kernel_rejects_bad_zero_anchor() -> None:
    with pytest.raises(InvalidCurveInput, match="tenor 0 must equal 1.0"):
        LogLinearDiscountKernel(
            tenors=[0.0, 5.0],
            discount_factors=[0.99, exp(-0.2)],
        )


def test_substep_d4_linear_zero_kernel_rejects_unsorted_tenors() -> None:
    with pytest.raises(InvalidCurveInput, match="strictly increasing"):
        LinearZeroKernel(
            tenors=[5.0, 1.0],
            zero_rates=[0.05, 0.03],
        )
