from __future__ import annotations

from math import exp

import pytest

from fuggers_py._core.types import Currency, Date
from fuggers_py.curves import CurveSpec, CurveType, ExtrapolationPolicy, YieldCurve
from fuggers_py.curves.errors import InvalidCurveInput, TenorOutOfBounds
from fuggers_py.curves.kernels import NelsonSiegelKernel, SvenssonKernel
from fuggers_py._math.interpolation.parametric import NelsonSiegel, Svensson


def _nominal_spec(*, extrapolation_policy: ExtrapolationPolicy = ExtrapolationPolicy.ERROR) -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type=CurveType.NOMINAL,
        extrapolation_policy=extrapolation_policy,
    )


def test_substep_d6_nelson_siegel_kernel_prices_through_yield_curve() -> None:
    model = NelsonSiegel.new(beta0=0.03, beta1=-0.01, beta2=0.02, tau=1.5)
    curve = YieldCurve(
        spec=_nominal_spec(),
        kernel=NelsonSiegelKernel(
            beta0=0.03,
            beta1=-0.01,
            beta2=0.02,
            tau=1.5,
            max_t=30.0,
        ),
    )

    expected_zero = model.interpolate(5.0)

    assert curve.rate_at(5.0) == pytest.approx(expected_zero)
    assert curve.zero_rate_at(5.0) == pytest.approx(expected_zero)
    assert curve.discount_factor_at(5.0) == pytest.approx(exp(-expected_zero * 5.0))


def test_substep_d6_svensson_kernel_matches_parametric_formula() -> None:
    model = Svensson.new(
        beta0=0.025,
        beta1=-0.01,
        beta2=0.02,
        beta3=-0.003,
        tau1=1.5,
        tau2=4.0,
    )
    kernel = SvenssonKernel(
        beta0=0.025,
        beta1=-0.01,
        beta2=0.02,
        beta3=-0.003,
        tau1=1.5,
        tau2=4.0,
        max_t=40.0,
    )

    assert kernel.rate_at(0.0) == pytest.approx(model.interpolate(0.0))
    assert kernel.rate_at(7.0) == pytest.approx(model.interpolate(7.0))
    assert kernel.discount_factor_at(7.0) == pytest.approx(exp(-model.interpolate(7.0) * 7.0))


def test_substep_d6_parametric_kernels_support_extrapolation_when_enabled() -> None:
    kernel = NelsonSiegelKernel(
        beta0=0.03,
        beta1=-0.01,
        beta2=0.02,
        tau=1.5,
        max_t=10.0,
        allow_extrapolation=True,
    )

    assert kernel.rate_at(15.0) == pytest.approx(
        NelsonSiegel.new(beta0=0.03, beta1=-0.01, beta2=0.02, tau=1.5).interpolate(15.0)
    )


def test_substep_d6_parametric_kernels_reject_extrapolation_when_disabled() -> None:
    kernel = SvenssonKernel(
        beta0=0.025,
        beta1=-0.01,
        beta2=0.02,
        beta3=-0.003,
        tau1=1.5,
        tau2=4.0,
        max_t=10.0,
    )

    with pytest.raises(TenorOutOfBounds):
        kernel.rate_at(15.0)


def test_substep_d6_parametric_kernels_validate_parameters() -> None:
    with pytest.raises(InvalidCurveInput, match="tau must be > 0"):
        NelsonSiegelKernel(
            beta0=0.03,
            beta1=-0.01,
            beta2=0.02,
            tau=0.0,
            max_t=30.0,
        )

    with pytest.raises(InvalidCurveInput, match="max_t must be > 0"):
        SvenssonKernel(
            beta0=0.025,
            beta1=-0.01,
            beta2=0.02,
            beta3=-0.003,
            tau1=1.5,
            tau2=4.0,
            max_t=0.0,
        )
