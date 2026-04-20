from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st

from fuggers_py._core import Compounding
from fuggers_py._curves_impl import BreakevenZeroCurve, FittedParYieldCurve, ParCurveSpec

from tests.helpers._fitted_bond_helpers import cubic_model, fit_result


PROPERTY_SETTINGS = settings(
    max_examples=8,
    deadline=None,
)


@PROPERTY_SETTINGS
@given(tenor=st.integers(min_value=2, max_value=10))
@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("properties")
def test_direct_par_curve_prices_selected_tenors_to_par(tenor: int) -> None:
    result = fit_result(curve_model=cubic_model(), regression_coefficient=Decimal("0"), regression_exposures={})
    par_curve = FittedParYieldCurve.from_fit_result(result, ParCurveSpec())
    coupon = par_curve.par_yield(Decimal(tenor))

    assert float(par_curve.clean_price(Decimal(tenor), coupon)) == pytest.approx(100.0, abs=1e-8)


@PROPERTY_SETTINGS
@given(
    nominal_rate=st.decimals(min_value="-0.20", max_value="0.20", places=4),
    real_rate=st.decimals(min_value="-0.20", max_value="0.20", places=4),
)
@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("properties")
def test_compounding_aware_zero_breakeven_matches_the_fisher_style_formula(
    nominal_rate: Decimal,
    real_rate: Decimal,
) -> None:
    expected = (Decimal(1) + nominal_rate) / (Decimal(1) + real_rate) - Decimal(1)

    result = BreakevenZeroCurve.rate_from_zero_rates(
        nominal_rate=nominal_rate,
        real_rate=real_rate,
        compounding=Compounding.ANNUAL,
    )

    assert float(result) == pytest.approx(float(expected), abs=1e-10)
