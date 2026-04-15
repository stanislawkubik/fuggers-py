from __future__ import annotations

from math import exp, sqrt

import pytest

from fuggers_py.core.types import Currency, Date
from fuggers_py.market.curves import (
    CurveSpec,
    CurveType,
    ExtrapolationPolicy,
    YieldCurve,
)
from fuggers_py.market.curves.errors import InvalidCurveInput, TenorOutOfBounds
from fuggers_py.market.curves.rates.kernels import (
    LinearZeroKernel,
    LogLinearDiscountKernel,
    MonotoneConvexKernel,
    PiecewiseConstantZeroKernel,
    PiecewiseFlatForwardKernel,
)


def _nominal_spec(*, extrapolation_policy: ExtrapolationPolicy = ExtrapolationPolicy.ERROR) -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type=CurveType.NOMINAL,
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
        spec=_nominal_spec(extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_NATIVE_RATE),
        kernel=LinearZeroKernel(
            tenors=[1.0, 5.0],
            zero_rates=[0.03, 0.05],
            allow_extrapolation=True,
        ),
    )

    assert curve.discount_factor_at(6.0) > 0.0


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
