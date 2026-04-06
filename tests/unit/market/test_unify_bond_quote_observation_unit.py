from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.market.quotes import BondQuote
from fuggers_py.market.curves import BondFairValueRequest, FittedBondCurveFitter
from fuggers_py.market.curves.fitted_bonds.fair_value import fair_value_from_fit

from tests.helpers._fitted_bond_helpers import (
    exponential_model,
    liquidity_regression_exposures,
    make_curve_observations,
    nominal_bond_lookup,
    nominal_fit_kwargs,
    nominal_reference_data_lookup,
    observation_regression_exposures,
)


@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("unit")
def test_clean_and_dirty_bondquote_paths_produce_the_same_nominal_fit() -> None:
    clean_observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.15"),
        quote_field="clean",
    )
    dirty_observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.15"),
        quote_field="dirty",
    )

    clean_result = FittedBondCurveFitter(
        curve_model=exponential_model(),
    ).fit(
        clean_observations,
        regression_exposures=liquidity_regression_exposures(clean_observations),
        **nominal_fit_kwargs(),
    )
    dirty_result = FittedBondCurveFitter(
        curve_model=exponential_model(),
    ).fit(
        dirty_observations,
        regression_exposures=liquidity_regression_exposures(dirty_observations),
        **nominal_fit_kwargs(),
    )

    clean_point = clean_result.get_bond("UST6Y")
    dirty_point = dirty_result.get_bond("UST6Y")

    assert float(clean_result.coefficient_map()["liquidity"]) == pytest.approx(
        float(dirty_result.coefficient_map()["liquidity"]),
        abs=1e-8,
    )
    assert float(clean_point["fitted_dirty_price"]) == pytest.approx(float(dirty_point["fitted_dirty_price"]), abs=1e-8)
    assert float(clean_point["fitted_yield"]) == pytest.approx(float(dirty_point["fitted_yield"]), abs=1e-10)


@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("unit")
def test_inconsistent_clean_and_dirty_bondquote_is_rejected() -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0"),
    )
    bad = observations[0]
    inconsistent_quote = BondQuote(
        instrument_id=bad.instrument_id,
        clean_price=bad.clean_price,
        dirty_price=(bad.clean_price or Decimal(0)) + Decimal("1.00"),
        as_of=bad.as_of,
    )

    with pytest.raises(ValueError, match="match accrued interest"):
        FittedBondCurveFitter(
            curve_model=exponential_model(),
        ).fit(
            (inconsistent_quote, *observations[1:]),
            regression_exposures={},
            **nominal_fit_kwargs(),
        )


@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("unit")
def test_fair_value_request_accepts_regular_bondquote() -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
    )
    result = FittedBondCurveFitter(
        curve_model=exponential_model(),
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )
    quote = observations[4]
    bond = nominal_bond_lookup()[quote.instrument_id.as_str()]
    reference_data = nominal_reference_data_lookup()[quote.instrument_id.as_str()]
    assert quote.as_of is not None
    point = result.get_bond(quote.instrument_id)

    fair_value = fair_value_from_fit(
        result,
        BondFairValueRequest(
            bond=bond,
            settlement_date=quote.as_of,
            instrument_id=quote.instrument_id,
            reference_data=reference_data,
            quote=quote,
            regression_exposures=observation_regression_exposures(quote),
        ),
    )

    assert float(fair_value.fair_value_dirty_price) == pytest.approx(float(point["fitted_dirty_price"]), abs=1e-6)
    assert float(fair_value.fair_value_clean_price) == pytest.approx(float(point["fitted_clean_price"]), abs=1e-6)
