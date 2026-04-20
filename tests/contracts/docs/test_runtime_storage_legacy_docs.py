from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT


def test_api_index_keeps_legacy_and_internal_pages_out_of_main_guide() -> None:
    text = (ROOT / "docs/api/index.md").read_text(encoding="utf-8")

    assert "\ncore\n" not in text
    assert "\nmath\n" not in text
    assert "\ncalc\n" not in text
    assert "\nadapters\n" not in text
    assert "Legacy and internal pages are kept outside this main guide on purpose." in text


def test_runtime_and_storage_pages_stay_legacy_notes() -> None:
    calc_text = (ROOT / "docs/api/calc.md").read_text(encoding="utf-8")
    adapters_text = (ROOT / "docs/api/adapters.md").read_text(encoding="utf-8")
    core_text = (ROOT / "docs/api/core.md").read_text(encoding="utf-8")
    math_text = (ROOT / "docs/api/math.md").read_text(encoding="utf-8")

    assert "Retired public namespace." in calc_text
    assert ".. automodule:: fuggers_py.calc" not in calc_text
    assert "Retired public namespace." in adapters_text
    assert ".. automodule:: fuggers_py.adapters" not in adapters_text
    assert "Retired public namespace." in core_text
    assert ".. automodule:: fuggers_py.core" not in core_text
    assert "Retired public namespace." in math_text
    assert ".. automodule:: fuggers_py.math" not in math_text


def test_module_reference_page_is_archived_and_readme_does_not_call_it_live_inventory() -> None:
    module_reference_text = (ROOT / "docs/MODULE_REFERENCE.md").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Archived note." in module_reference_text
    assert "no longer the live source-tree inventory" in module_reference_text
    assert "SRC_STRUCTURE.md" in module_reference_text
    assert "docs/api/index.md" in module_reference_text
    assert "live source tree" not in readme_text
