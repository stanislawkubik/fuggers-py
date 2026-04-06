from __future__ import annotations

import pytest

from tests.helpers._paths import REPO_ROOT


@pytest.mark.feature_slug("fitted-bond-optional-regressors")
@pytest.mark.feature_category("examples_smoke")
def test_examples_catalog_includes_readme() -> None:
    assert (REPO_ROOT / "examples" / "README.md").exists()
