from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from fuggers_py.core import Compounding, Date
from fuggers_py.market.curves import CreditCurve, DiscountCurveBuilder, ValueConverter
from fuggers_py.market.curves.calibration import FitterConfig, GlobalFitter, ParametricModel
from fuggers_py.market.curves.term_structure import TermStructure
from fuggers_py.market.curves.value_type import ValueType

from ._helpers import D, assert_decimal_close, load_fixture, parse_date


pytestmark = pytest.mark.validation


def _ns_zero(t: float, beta0: float, beta1: float, beta2: float, tau: float) -> float:
    if t <= 0.0:
        return beta0 + beta1
    x = t / tau
    exp_x = np.exp(-x)
    factor = (1.0 - exp_x) / x
    return float(beta0 + beta1 * factor + beta2 * (factor - exp_x))


def _sv_zero(t: float, beta0: float, beta1: float, beta2: float, beta3: float, tau1: float, tau2: float) -> float:
    if t <= 0.0:
        return beta0 + beta1
    x1 = t / tau1
    x2 = t / tau2
    exp1 = np.exp(-x1)
    exp2 = np.exp(-x2)
    factor1 = (1.0 - exp1) / x1
    factor2 = (1.0 - exp2) / x2
    return float(beta0 + beta1 * factor1 + beta2 * (factor1 - exp1) + beta3 * (factor2 - exp2))


def test_curve_conversion_reference_cases_round_trip_cleanly() -> None:
    fixture = load_fixture("curves", "conversion.json")
    roundtrip = fixture["compounding_roundtrip"]
    zero_rate = float(roundtrip["zero_rate"])
    tenor = float(roundtrip["tenor"])
    compounding = Compounding[roundtrip["compounding"]]
    df = ValueConverter.zero_to_df(zero_rate, tenor, compounding)
    zero_roundtrip = ValueConverter.df_to_zero(df, tenor, compounding)

    assert df == pytest.approx(float(roundtrip["expected_discount_factor"]), abs=1e-15)
    assert zero_roundtrip == pytest.approx(float(roundtrip["expected_zero_roundtrip"]), abs=1e-15)

    forward_case = fixture["forward_from_zeros"]
    forward = ValueConverter.forward_rate_from_zeros(
        float(forward_case["zero1"]),
        float(forward_case["zero2"]),
        float(forward_case["tenor1"]),
        float(forward_case["tenor2"]),
    )
    curve = (
        DiscountCurveBuilder(reference_date=parse_date(forward_case["reference_date"]))
        .add_zero_rate(float(forward_case["tenor1"]), D(forward_case["zero1"]))
        .add_zero_rate(float(forward_case["tenor2"]), D(forward_case["zero2"]))
        .build()
    )
    df1 = curve.discount_factor_at_tenor(float(forward_case["tenor1"]))
    df2 = curve.discount_factor_at_tenor(float(forward_case["tenor2"]))
    forward_from_dfs = ValueConverter.forward_rate_from_dfs(
        df1,
        df2,
        float(forward_case["tenor1"]),
        float(forward_case["tenor2"]),
        Compounding.CONTINUOUS,
    )

    assert forward == pytest.approx(float(forward_case["expected_forward_rate"]), abs=1e-15)
    assert forward_from_dfs == pytest.approx(float(forward_case["expected_forward_rate"]), abs=1e-15)

    hazard_case = fixture["hazard_survival"]
    survival = ValueConverter.hazard_to_survival(float(hazard_case["hazard_rate"]), float(hazard_case["tenor"]))
    implied_hazard = ValueConverter.implied_hazard_rate(survival, float(hazard_case["tenor"]))

    assert survival == pytest.approx(float(hazard_case["expected_survival_probability"]), abs=1e-15)
    assert implied_hazard == pytest.approx(float(hazard_case["expected_hazard_roundtrip"]), abs=1e-15)


def test_global_fit_matches_synthetic_nelson_siegel_and_svensson_references() -> None:
    fixture = load_fixture("curves", "global_fit.json")

    ns_case = fixture["nelson_siegel_synthetic"]
    ns_tenors = np.array([float(value) for value in ns_case["tenors"]], dtype=float)
    ns_true = np.array([float(value) for value in ns_case["true_parameters"]], dtype=float)
    ns_observed = np.array([_ns_zero(t, *ns_true) for t in ns_tenors], dtype=float)
    ns_fit = GlobalFitter(parse_date(ns_case["reference_date"]), config=FitterConfig(model=ParametricModel.NELSON_SIEGEL)).fit_zero_rates(ns_tenors, ns_observed)

    assert ns_fit.converged is True
    assert ns_fit.objective_value <= float(ns_case["objective_tolerance"])
    assert np.allclose(ns_fit.parameters, ns_true, atol=float(ns_case["parameter_tolerance"]), rtol=0.0)

    sv_case = fixture["svensson_synthetic"]
    sv_tenors = np.array([float(value) for value in sv_case["tenors"]], dtype=float)
    sv_true = np.array([float(value) for value in sv_case["true_parameters"]], dtype=float)
    sv_observed = np.array([_sv_zero(t, *sv_true) for t in sv_tenors], dtype=float)
    sv_fit = GlobalFitter(
        parse_date(sv_case["reference_date"]),
        config=FitterConfig(
            model=ParametricModel.SVENSSON,
            initial_parameters=np.array([float(value) for value in sv_case["initial_parameters"]], dtype=float),
        ),
    ).fit_zero_rates(sv_tenors, sv_observed)

    assert sv_fit.converged is True
    assert sv_fit.objective_value <= float(sv_case["objective_tolerance"])
    assert np.allclose(sv_fit.parameters, sv_true, atol=float(sv_case["parameter_tolerance"]), rtol=0.0)


def test_credit_curve_survival_hazard_and_spread_match_flat_reference_formulas() -> None:
    fixture = load_fixture("curves", "credit_curve.json")

    class FlatCurve(TermStructure):
        def __init__(self, reference_date: Date, value: float, value_type: ValueType) -> None:
            self._reference_date = reference_date
            self._value = float(value)
            self._value_type = value_type

        def date(self) -> Date:
            return self._reference_date

        def value_at_tenor(self, t: float) -> float:
            return self._value

        def value_type(self) -> ValueType:
            return self._value_type

    hazard_case = fixture["flat_hazard_curve"]
    hazard_curve = CreditCurve(
        FlatCurve(parse_date(hazard_case["reference_date"]), float(hazard_case["hazard_rate"]), ValueType.hazard_rate()),
        recovery_rate=D(hazard_case["recovery_rate"]),
    )
    assert_decimal_close(
        hazard_curve.survival_probability_at_tenor(float(hazard_case["tenor"])),
        D(hazard_case["expected_survival_probability"]),
        Decimal("1e-15"),
    )
    assert_decimal_close(
        hazard_curve.credit_spread_at_tenor(float(hazard_case["tenor"])),
        D(hazard_case["expected_credit_spread"]),
        Decimal("1e-15"),
    )

    survival_case = fixture["flat_survival_curve"]
    survival_curve = CreditCurve(
        FlatCurve(
            parse_date(survival_case["reference_date"]),
            float(survival_case["survival_probability"]),
            ValueType.survival_probability(),
        ),
        recovery_rate=D(survival_case["recovery_rate"]),
    )
    assert_decimal_close(
        survival_curve.hazard_rate_at_tenor(float(survival_case["tenor"])),
        D(survival_case["expected_hazard_rate"]),
        Decimal("1e-15"),
    )
