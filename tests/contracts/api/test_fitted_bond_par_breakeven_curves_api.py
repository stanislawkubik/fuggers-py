from __future__ import annotations

import pytest

import fuggers_py.curves as curves


@pytest.mark.feature_slug("fitted-bond-par-breakeven-curves")
@pytest.mark.feature_category("api_contract")
def test_par_and_breakeven_curve_shape_names_are_not_part_of_the_current_public_curve_story() -> None:
    removed_names = (
        "ParCurveSpec",
        "FittedParYieldCurve",
        "BreakevenZeroCurve",
        "BreakevenParCurve",
    )

    for name in removed_names:
        assert not hasattr(curves, name)
