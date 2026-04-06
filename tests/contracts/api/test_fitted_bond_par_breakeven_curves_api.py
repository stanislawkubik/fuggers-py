from __future__ import annotations

import pytest

from fuggers_py.market import curves as market_curves
from fuggers_py.market.curves import BreakevenParCurve, BreakevenZeroCurve, FittedParYieldCurve, ParCurveSpec
from fuggers_py.market.curves import fitted_bonds, inflation


@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("api_contract")
def test_public_exports_expose_the_par_and_breakeven_curve_objects() -> None:
    assert market_curves.ParCurveSpec is ParCurveSpec
    assert market_curves.FittedParYieldCurve is FittedParYieldCurve
    assert market_curves.BreakevenZeroCurve is BreakevenZeroCurve
    assert market_curves.BreakevenParCurve is BreakevenParCurve
    assert fitted_bonds.ParCurveSpec is ParCurveSpec
    assert fitted_bonds.FittedParYieldCurve is FittedParYieldCurve
    assert inflation.BreakevenZeroCurve is BreakevenZeroCurve
    assert inflation.BreakevenParCurve is BreakevenParCurve
