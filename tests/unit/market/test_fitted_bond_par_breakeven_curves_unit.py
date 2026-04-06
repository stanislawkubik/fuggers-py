from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest

from fuggers_py.core import Compounding, InstrumentId
from fuggers_py.market.curves import (
    BreakevenParCurve,
    BreakevenZeroCurve,
    CubicSplineZeroRateCurveModel,
    FittedBondCurve,
    FittedParYieldCurve,
    ParCurveSpec,
)
from fuggers_py.market.curves.fitted_bonds.notional_benchmarks import NotionalBenchmark
from fuggers_py.measures.rv import generate_constant_maturity_benchmark

from tests.helpers._fitted_bond_helpers import REFERENCE_DATE, cubic_model, fit_result


def _weighted_coupon_from_benchmark(
    result: FittedBondCurve,
    benchmark: NotionalBenchmark,
) -> Decimal:
    total = Decimal(0)
    for component in benchmark.components:
        point = result.get_bond(InstrumentId.parse(component.instrument_id))
        total += component.weight * (point["coupon_rate"] or point["fitted_yield"])
    return total


@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("unit")
def test_direct_fitted_par_curve_prices_the_synthetic_bond_to_par() -> None:
    result = fit_result(curve_model=cubic_model(), regression_coefficient=Decimal("0.25"))
    par_curve = FittedParYieldCurve.from_fit_result(result, ParCurveSpec())
    tenor = Decimal("6.0")
    coupon = par_curve.par_yield(tenor)

    assert float(par_curve.clean_price(tenor, coupon)) == pytest.approx(100.0, abs=1e-8)
    assert float(par_curve.yield_to_maturity(tenor, coupon)) == pytest.approx(float(coupon), abs=1e-8)


@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("unit")
def test_constant_maturity_benchmark_uses_the_direct_par_curve_path() -> None:
    result = fit_result(curve_model=cubic_model(), regression_coefficient=Decimal("0.25"))
    target = Decimal("7.25")
    direct_par_curve = FittedParYieldCurve.from_fit_result(result, ParCurveSpec())

    benchmark = generate_constant_maturity_benchmark(
        result,
        target,
        component_count=2,
    )
    weighted_coupon = _weighted_coupon_from_benchmark(result, benchmark.benchmark)

    assert float(benchmark.coupon_rate) == pytest.approx(float(direct_par_curve.par_yield(target)), abs=1e-8)
    assert float(benchmark.fair_value_clean_price) == pytest.approx(100.0, abs=1e-8)
    assert abs(benchmark.coupon_rate - weighted_coupon) > Decimal("0.0001")


@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("unit")
def test_breakeven_zero_curve_matches_synthetic_nominal_and_real_zero_curves() -> None:
    model = CubicSplineZeroRateCurveModel(
        (
            Decimal("2.0"),
            Decimal("4.0"),
            Decimal("6.0"),
            Decimal("8.0"),
            Decimal("10.0"),
        )
    )
    nominal_curve = model.build_curve(
        REFERENCE_DATE,
        np.asarray([0.05, 0.05, 0.05, 0.05, 0.05], dtype=float),
        max_t=10.0,
    )
    real_curve = model.build_curve(
        REFERENCE_DATE,
        np.asarray([0.02, 0.02, 0.02, 0.02, 0.02], dtype=float),
        max_t=10.0,
    )
    breakeven_curve = BreakevenZeroCurve(
        nominal_curve=nominal_curve,
        real_curve=real_curve,
        compounding=Compounding.ANNUAL,
    )

    assert float(breakeven_curve.zero_breakeven(Decimal("5.0"))) == pytest.approx(math.exp(0.03) - 1.0, abs=1e-10)
    assert float(breakeven_curve.discount_factor(Decimal("5.0"))) == pytest.approx(math.exp(0.15), abs=1e-10)


@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("unit")
def test_breakeven_par_curve_returns_expected_sampled_differences() -> None:
    model = CubicSplineZeroRateCurveModel(
        (
            Decimal("2.0"),
            Decimal("4.0"),
            Decimal("6.0"),
            Decimal("8.0"),
            Decimal("10.0"),
        )
    )
    nominal_curve = model.build_curve(
        REFERENCE_DATE,
        np.asarray([0.05, 0.05, 0.05, 0.05, 0.05], dtype=float),
        max_t=10.0,
    )
    real_curve = model.build_curve(
        REFERENCE_DATE,
        np.asarray([0.02, 0.02, 0.02, 0.02, 0.02], dtype=float),
        max_t=10.0,
    )
    nominal_par_curve = FittedParYieldCurve(nominal_curve, ParCurveSpec())
    real_par_curve = FittedParYieldCurve(real_curve, ParCurveSpec())
    breakeven_par_curve = BreakevenParCurve.from_par_curves(
        nominal_par_curve,
        real_par_curve,
    )
    tenors = (Decimal("2.0"), Decimal("5.0"), Decimal("10.0"))
    expected = tuple(
        nominal_par_curve.par_yield(tenor) - real_par_curve.par_yield(tenor)
        for tenor in tenors
    )

    assert breakeven_par_curve.sample(tenors) == expected
