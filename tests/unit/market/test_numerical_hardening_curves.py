from __future__ import annotations

import numpy as np
import pytest

from fuggers_py.core import Compounding, Date
from fuggers_py.market.curves.calibration.global_fit import FitterConfig, GlobalFitter
from fuggers_py.market.curves.conversion import ValueConverter
from fuggers_py.market.curves.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py.market.curves.errors import InvalidCurveInput
from fuggers_py.market.curves.value_type import ValueType
from fuggers_py.market.curves.wrappers import CreditCurve
from fuggers_py.math.optimization import OptimizationConfig


def test_value_converter_rejects_invalid_discount_factors() -> None:
    with pytest.raises(InvalidCurveInput):
        ValueConverter.df_to_zero(0.0, 1.0, Compounding.CONTINUOUS)

    with pytest.raises(InvalidCurveInput):
        ValueConverter.zero_to_df(-2.0, 1.0, Compounding.ANNUAL)


def test_value_converter_rejects_invalid_credit_probabilities() -> None:
    with pytest.raises(InvalidCurveInput):
        ValueConverter.implied_hazard_rate(1.2, 1.0)

    with pytest.raises(InvalidCurveInput):
        ValueConverter.survival_to_hazard(0.95, 0.10)


def test_global_fitter_respects_observed_zero_rate_compounding() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    config = FitterConfig(
        compounding=Compounding.ANNUAL,
        optimization=OptimizationConfig(max_iterations=100, tolerance=1e-12),
    )
    result = GlobalFitter(ref, config=config).fit_zero_rates(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.05, 0.05, 0.05]),
    )

    assert result.curve.zero_rate_at_tenor(2.0, compounding=Compounding.ANNUAL) == pytest.approx(0.05, abs=1e-4)


def test_global_fitter_reparameterizes_negative_tau_initial_guess() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    config = FitterConfig(
        initial_parameters=np.array([0.04, -0.01, 0.0, -2.0]),
        optimization=OptimizationConfig(max_iterations=50, tolerance=1e-10),
    )
    result = GlobalFitter(ref, config=config).fit_zero_rates(
        tenors=np.array([1.0, 2.0, 5.0]),
        zero_rates=np.array([0.04, 0.04, 0.04]),
    )

    assert result.parameters[3] > 0.0


def test_credit_curve_rejects_negative_hazard_values() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    inner = DiscreteCurve(
        ref,
        tenors=[1.0, 5.0],
        values=[-0.01, -0.01],
        value_type=ValueType.hazard_rate(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    credit_curve = CreditCurve(inner)

    with pytest.raises(InvalidCurveInput):
        credit_curve.survival_probability_at_tenor(2.0)
