from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from fuggers_py._core import Tenor
from fuggers_py._core import Compounding, Date
from fuggers_py._curves_impl.calibration.global_fit import FitterConfig, GlobalFitter
from fuggers_py._curves_impl.calibration.instruments import Deposit, InstrumentSet
from fuggers_py._curves_impl.conversion import ValueConverter
from fuggers_py._curves_impl.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py._curves_impl.errors import InvalidCurveInput, UnsupportedValueType
from fuggers_py._curves_impl.value_type import ValueType
from fuggers_py._curves_impl.wrappers import CreditCurve
from fuggers_py._math.optimization import OptimizationConfig


def test_value_converter_validates_forward_inputs_and_risky_discount_factor_formula() -> None:
    with pytest.raises(InvalidCurveInput):
        ValueConverter.forward_rate_from_dfs(0.99, 0.98, 2.0, 2.0, Compounding.CONTINUOUS)

    risky_df = ValueConverter.risky_discount_factor(0.95, 0.90, 0.40)

    assert risky_df == pytest.approx(0.95 * (0.90 + (1.0 - 0.90) * 0.40), abs=1e-12)


def test_credit_curve_rejects_invalid_recovery_survival_and_value_types() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    survival_curve = DiscreteCurve(
        ref,
        tenors=[1.0, 5.0],
        values=[1.05, 1.02],
        value_type=ValueType.survival_probability(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    unsupported_curve = DiscreteCurve(
        ref,
        tenors=[1.0, 5.0],
        values=[0.03, 0.035],
        value_type=ValueType.zero_rate(Compounding.CONTINUOUS),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )

    with pytest.raises(InvalidCurveInput):
        CreditCurve(unsupported_curve, recovery_rate=Decimal("1.0"))

    with pytest.raises(InvalidCurveInput):
        CreditCurve(survival_curve).survival_probability_at_tenor(2.0)

    with pytest.raises(UnsupportedValueType):
        CreditCurve(unsupported_curve).hazard_rate_at_tenor(2.0)


def test_global_fitter_validates_inputs_and_initial_parameter_length() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    fitter = GlobalFitter(ref)

    with pytest.raises(InvalidCurveInput):
        fitter.fit_zero_rates(np.array([[1.0, 2.0]]), np.array([0.03, 0.04]))

    with pytest.raises(InvalidCurveInput):
        fitter.fit_zero_rates(np.array([1.0, 2.0]), np.array([0.03]))

    with pytest.raises(InvalidCurveInput):
        fitter.fit_zero_rates(np.array([0.0, 2.0]), np.array([0.03, 0.04]))

    with pytest.raises(InvalidCurveInput):
        fitter.fit_zero_rates(np.array([1.0, np.nan]), np.array([0.03, 0.04]))

    bad_initial = FitterConfig(initial_parameters=np.array([0.03, 0.04]))
    with pytest.raises(InvalidCurveInput):
        GlobalFitter(ref, config=bad_initial).fit_zero_rates(np.array([1.0, 3.0]), np.array([0.03, 0.035]))


def test_global_fitter_can_fit_simple_deposit_instruments_close_to_quotes() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    instruments = InstrumentSet(
        [
            Deposit(ref, Decimal("0.03"), tenor=Tenor.parse("1Y")),
            Deposit(ref, Decimal("0.032"), tenor=Tenor.parse("3Y")),
            Deposit(ref, Decimal("0.035"), tenor=Tenor.parse("5Y")),
            Deposit(ref, Decimal("0.038"), tenor=Tenor.parse("10Y")),
        ]
    )
    fitter = GlobalFitter(
        ref,
        config=FitterConfig(optimization=OptimizationConfig(max_iterations=200, tolerance=1e-12)),
    )

    result = fitter.fit_instruments(instruments)

    assert result.parameters.shape == (4,)
    assert result.curve.zero_rate_at_tenor(1.0) > 0.0
    for instrument in instruments.instruments:
        assert float(instrument.par_rate(result.curve)) == pytest.approx(float(instrument.quote), abs=5e-4)
