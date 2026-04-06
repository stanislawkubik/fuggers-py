from __future__ import annotations

import json
import re

import pytest

from tests.helpers._paths import REPO_ROOT


NOTEBOOK_PATH = REPO_ROOT / "examples" / "05_fitted_nominal_real_breakeven_minimal.ipynb"


def _load_source() -> str:
    with NOTEBOOK_PATH.open("r", encoding="utf-8") as handle:
        notebook = json.load(handle)
    return "\n".join("".join(cell["source"]) for cell in notebook["cells"])


@pytest.mark.feature_slug("fitted-bond-minimal-breakeven-notebook")
@pytest.mark.feature_category("properties")
def test_minimal_breakeven_notebook_keeps_the_requested_synthetic_cross_section_sizes_and_stays_self_contained() -> None:
    source = _load_source()
    nominal_ids = set(re.findall(r"['\"]UST\d+Y['\"]", source))
    tips_ids = set(re.findall(r"['\"]TIPS\d+Y['\"]", source))
    banned_patterns = (
        "read_csv",
        ".csv",
        "synthetic_data",
        "requests.",
        "http://",
        "https://",
        "Bloomberg",
    )

    assert 5 <= len(nominal_ids) <= 8
    assert 4 <= len(tips_ids) <= 6
    for pattern in banned_patterns:
        assert pattern not in source
