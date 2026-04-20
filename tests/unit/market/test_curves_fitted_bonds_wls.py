from __future__ import annotations

from decimal import Decimal

from fuggers_py._curves_impl import BondCurveFitter, CurveObjective

from tests.helpers._fitted_bond_helpers import (
    exponential_model,
    liquidity_regression_exposures,
    make_observations,
    nominal_fit_kwargs,
)


def test_weighted_fit_prioritizes_high_weight_observations_over_a_low_weight_outlier() -> None:
    outlier = {"UST10Y": Decimal("1.20")}
    unweighted_observations, _ = make_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
        mispricings=outlier,
    )
    weighted_observations, _ = make_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
        mispricings=outlier,
        weights={
            "UST2Y": Decimal("5"),
            "UST3Y": Decimal("5"),
            "UST4Y": Decimal("5"),
            "UST5Y": Decimal("5"),
            "UST6Y": Decimal("5"),
            "UST8Y": Decimal("5"),
            "UST10Y": Decimal("0.10"),
        },
    )
    fitter = BondCurveFitter(
        curve_model=exponential_model(),
        objective=CurveObjective.L2,
    )
    unweighted = fitter.fit(
        unweighted_observations,
        regression_exposures=liquidity_regression_exposures(unweighted_observations),
        **nominal_fit_kwargs(),
    )
    weighted = fitter.fit(
        weighted_observations,
        regression_exposures=liquidity_regression_exposures(weighted_observations),
        **nominal_fit_kwargs(
            weights={
                "UST2Y": Decimal("5"),
                "UST3Y": Decimal("5"),
                "UST4Y": Decimal("5"),
                "UST5Y": Decimal("5"),
                "UST6Y": Decimal("5"),
                "UST8Y": Decimal("5"),
                "UST10Y": Decimal("0.10"),
            }
        ),
    )

    assert abs(weighted.get_bond("UST5Y")["price_residual"]) < abs(unweighted.get_bond("UST5Y")["price_residual"])
    assert abs(weighted.get_bond("UST10Y")["price_residual"]) > abs(unweighted.get_bond("UST10Y")["price_residual"])


def test_l1_objective_is_more_robust_to_the_same_outlier_than_l2() -> None:
    observations, _ = make_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
        mispricings={"UST10Y": Decimal("1.20")},
    )
    l2_fit = BondCurveFitter(
        curve_model=exponential_model(),
        objective=CurveObjective.L2,
    ).fit(observations, regression_exposures=liquidity_regression_exposures(observations), **nominal_fit_kwargs())
    l1_fit = BondCurveFitter(
        curve_model=exponential_model(),
        objective=CurveObjective.L1,
    ).fit(observations, regression_exposures=liquidity_regression_exposures(observations), **nominal_fit_kwargs())

    l2_total_abs = sum(abs(point["price_residual"]) for point in l2_fit.bonds)
    l1_total_abs = sum(abs(point["price_residual"]) for point in l1_fit.bonds)

    assert l1_fit.objective is CurveObjective.L1
    assert l1_total_abs <= l2_total_abs
