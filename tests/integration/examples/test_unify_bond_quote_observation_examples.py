from __future__ import annotations

import json
from typing import Any, cast

import pytest

from tests.helpers._paths import REPO_ROOT


NOTEBOOK_PATH = REPO_ROOT / "examples" / "05_fitted_nominal_real_breakeven_minimal.ipynb"


def _joined_source() -> str:
    notebook = cast(dict[str, Any], json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8")))
    cells = cast(list[dict[str, Any]], notebook["cells"])
    return "\n".join("".join(cast(list[str], cell["source"])) for cell in cells)


@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("examples_smoke")
def test_breakeven_notebook_uses_one_bondquote_surface() -> None:
    source = _joined_source()

    assert "BondQuote(" in source
    assert "instrument=bond" in source
    assert "as_of=REFERENCE_DATE" in source
    assert "BondObservation(" not in source
    assert "FittedBondCurveFitter" not in source
    assert "FittedBondObservation" not in source
    assert "bonds=nominal_bonds" not in source
    assert "bonds=tips_bonds" not in source
    assert "BondCurveQuote" not in source
    assert "BondCurveQuoteBasis" not in source
    assert "BondCurveObservation" not in source
