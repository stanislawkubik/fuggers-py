from __future__ import annotations

import pytest

from tests.helpers._paths import REPO_ROOT


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("examples_smoke")
def test_examples_catalog_readme_exists_for_flat_examples_root() -> None:
    readme_path = REPO_ROOT / "examples" / "README.md"

    assert readme_path.exists()
    assert "01_cash_bond_and_curve_workflow.ipynb" in readme_path.read_text(
        encoding="utf-8"
    )
