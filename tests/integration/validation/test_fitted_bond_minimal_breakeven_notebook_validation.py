from __future__ import annotations

import json
from typing import Any, cast

import pytest

from tests.helpers._paths import REPO_ROOT


NOTEBOOK_PATH = REPO_ROOT / "examples" / "05_fitted_nominal_real_breakeven_minimal.ipynb"


def _load_notebook() -> dict[str, Any]:
    with NOTEBOOK_PATH.open("r", encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


@pytest.mark.feature_slug("fitted-bond-minimal-breakeven-notebook")
@pytest.mark.feature_category("validation")
def test_minimal_breakeven_notebook_has_sectioned_methodology_and_inline_synthetic_inputs() -> None:
    notebook = _load_notebook()
    cells = cast(list[dict[str, Any]], notebook["cells"])
    markdown_cells = [cell for cell in cells if cell["cell_type"] == "markdown"]
    markdown_source = "".join(cast(list[str], markdown_cells[0]["source"]))
    code_source = "\n".join("".join(cast(list[str], cell["source"])) for cell in cells if cell["cell_type"] == "code")

    assert len(markdown_cells) == 5
    assert "price space" in markdown_source
    assert "dirty-price space internally" in markdown_source
    assert "no external regressors" in markdown_source
    assert "derive direct par curves" in markdown_source
    assert "zero breakeven plus par breakeven" in markdown_source
    assert "## 1. Setup" in "".join(cast(list[str], markdown_cells[1]["source"]))
    assert "## 2. Synthetic Observations" in "".join(cast(list[str], markdown_cells[2]["source"]))
    assert "## 3. Fit The Curves" in "".join(cast(list[str], markdown_cells[3]["source"]))
    assert "## 4. Par And Breakeven Views" in "".join(cast(list[str], markdown_cells[4]["source"]))
    assert "nominal_inputs = [" in code_source
    assert "tips_inputs = [" in code_source
    assert "make_fixing_source" in code_source
