from __future__ import annotations

import pytest

from tests.helpers._paths import REPO_ROOT
from tests.integration.examples.test_examples_smoke import EXPECTED_NOTEBOOKS


NOTEBOOK_PATH = REPO_ROOT / "examples" / "05_fitted_nominal_real_breakeven_minimal.ipynb"


@pytest.mark.feature_slug("fitted-bond-minimal-breakeven-notebook")
@pytest.mark.feature_category("examples_smoke")
def test_minimal_breakeven_notebook_is_in_the_smoke_catalog_and_is_readable() -> None:
    nbformat = pytest.importorskip("nbformat")

    notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)

    assert NOTEBOOK_PATH.name in EXPECTED_NOTEBOOKS
    assert len(notebook.cells) == 12
    assert notebook.cells[0].cell_type == "markdown"
    assert notebook.cells[2].cell_type == "markdown"
    assert notebook.cells[4].cell_type == "markdown"
