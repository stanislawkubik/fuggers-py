from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Compounding
from fuggers_py._curves_impl import BreakevenParCurve, BreakevenZeroCurve, FittedParYieldCurve, ParCurveSpec

from tests.helpers._fitted_bond_helpers import cubic_model, fit_result, tips_fit_result


@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("validation")
def test_zero_and_par_breakeven_curves_are_near_zero_when_nominal_and_real_fits_match() -> None:
    nominal_result = fit_result(
        curve_model=cubic_model(),
        regression_coefficient=Decimal("0"),
        regression_exposures={},
    )
    real_result = tips_fit_result(
        curve_model=cubic_model(),
        regression_coefficient=Decimal("0"),
        regression_exposures={},
    )

    zero_curve = BreakevenZeroCurve.from_fitted_curves(
        nominal_result,
        real_result,
        compounding=Compounding.CONTINUOUS,
    )
    par_curve = BreakevenParCurve.from_par_curves(
        FittedParYieldCurve.from_fit_result(nominal_result, ParCurveSpec()),
        FittedParYieldCurve.from_fit_result(real_result, ParCurveSpec()),
    )

    assert float(zero_curve.zero_breakeven(Decimal("5.0"))) == pytest.approx(0.0, abs=1e-6)
    assert float(par_curve.par_breakeven(Decimal("5.0"))) == pytest.approx(0.0, abs=1e-6)
