from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Compounding, Date
from fuggers_py.curves import (
    CalibrationReport,
    CurveSpec,
    YieldCurve,
)
from fuggers_py.curves.conversion import ValueConverter
from fuggers_py.curves.kernels.nodes import LinearZeroKernel, LogLinearDiscountKernel
from fuggers_py.rates import SwapQuote

from ._helpers import load_fixture


pytestmark = pytest.mark.validation


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
    curve = YieldCurve(
        spec=CurveSpec(
            name="validation.zero",
            reference_date=Date.parse(forward_case["reference_date"]),
            day_count="ACT/365F",
            currency="USD",
            type="nominal",
            extrapolation_policy="error",
        ),
        kernel=LinearZeroKernel(
            tenors=(float(forward_case["tenor1"]), float(forward_case["tenor2"])),
            zero_rates=(float(forward_case["zero1"]), float(forward_case["zero2"])),
        ),
    )
    forward_from_dfs = ValueConverter.forward_rate_from_dfs(
        curve.discount_factor_at(float(forward_case["tenor1"])),
        curve.discount_factor_at(float(forward_case["tenor2"])),
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


def test_public_yield_curve_fit_matches_swap_quote_nodes() -> None:
    reference_date = Date.from_ymd(2026, 4, 9)
    curve = YieldCurve.fit(
        quotes=(
            SwapQuote(instrument_id="1Y", tenor="1Y", rate=0.025, currency="USD", as_of=reference_date),
            SwapQuote(instrument_id="2Y", tenor="2Y", rate=0.030, currency="USD", as_of=reference_date),
            SwapQuote(instrument_id="5Y", tenor="5Y", rate=0.035, currency="USD", as_of=reference_date),
        ),
        spec=CurveSpec(
            name="USD OIS",
            reference_date=reference_date,
            day_count="ACT/365F",
            currency="USD",
            type="overnight_discount",
            extrapolation_policy="hold_last_zero_rate",
        ),
        kernel="cubic_spline",
        method="global_fit",
        kernel_params={"knots": (1.0, 2.0, 5.0)},
    )

    assert isinstance(curve, YieldCurve)
    assert curve.rate_at(1.0) == pytest.approx(0.025, abs=1e-12)
    assert curve.rate_at(2.0) == pytest.approx(0.030, abs=1e-12)
    assert curve.rate_at(5.0) == pytest.approx(0.035, abs=1e-12)
    assert isinstance(curve.calibration_report, CalibrationReport)


def test_manual_discount_curve_keeps_positive_discounts_and_forwards() -> None:
    reference_date = Date.from_ymd(2026, 4, 9)
    curve = YieldCurve(
        spec=CurveSpec(
            name="validation.discount",
            reference_date=reference_date,
            day_count="ACT/365F",
            currency="USD",
            type="overnight_discount",
            extrapolation_policy="error",
        ),
        kernel=LogLinearDiscountKernel(
            tenors=(1.0, 2.0, 5.0),
            discount_factors=(0.98, 0.94, 0.84),
        ),
    )

    assert Decimal(str(curve.discount_factor_at(1.0))) > Decimal(0)
    assert Decimal(str(curve.discount_factor_at(5.0))) > Decimal(0)
    assert curve.forward_rate_between(1.0, 5.0) > 0.0
