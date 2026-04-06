from __future__ import annotations

import json
from typing import Any, cast

import pytest

from tests.helpers._paths import REPO_ROOT


NOTEBOOK_PATH = REPO_ROOT / "examples" / "05_fitted_nominal_real_breakeven_minimal.ipynb"


def _load_notebook() -> dict[str, Any]:
    with NOTEBOOK_PATH.open("r", encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


def _joined_source(notebook: dict[str, Any]) -> str:
    cells = cast(list[dict[str, Any]], notebook["cells"])
    return "\n".join("".join(cast(list[str], cell["source"])) for cell in cells)


@pytest.mark.feature_slug("fitted-bond-minimal-breakeven-notebook")
@pytest.mark.feature_category("unit")
def test_minimal_breakeven_notebook_uses_the_required_public_api_surface() -> None:
    notebook = _load_notebook()
    source = _joined_source(notebook)

    assert NOTEBOOK_PATH.exists()
    assert "FittedBondCurveFitter" in source
    assert "CubicSplineZeroRateCurveModel" in source
    assert "NominalGovernmentBondPricingAdapter" in source
    assert "TipsRealBondPricingAdapter" in source
    assert "FittedParYieldCurve" in source
    assert "BreakevenZeroCurve" in source
    assert "BreakevenParCurve" in source
    assert "BondQuote(" in source
    assert "nominal_bonds =" in source
    assert "tips_bonds =" in source
    assert "bonds=nominal_bonds" in source
    assert "bonds=tips_bonds" in source
    assert "settlement_date=REFERENCE_DATE" in source
    assert "BondObservation(" not in source
    assert "FittedBondObservation" not in source
    assert "regression_exposures={}" in source
