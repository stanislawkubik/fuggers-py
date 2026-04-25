from __future__ import annotations

from pathlib import Path

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
PACKAGE_ROOT = ROOT / "src" / "fuggers_py"
INTERNAL_ROOTS = ("_core", "_math", "_runtime", "_storage")
PUBLIC_ROOTS = ("bonds", "credit", "curves", "funding", "inflation", "portfolio", "rates", "vol_surfaces")


def _dev_internal_docs_text() -> str:
    return (ROOT / "docs/dev/internal_modules.md").read_text(encoding="utf-8")


def _relative_package_path(path: Path) -> str:
    return path.relative_to(PACKAGE_ROOT).as_posix()


def _internal_root_python_paths() -> list[str]:
    paths: list[str] = []
    for root_name in INTERNAL_ROOTS:
        root = PACKAGE_ROOT / root_name
        paths.extend(
            _relative_package_path(path)
            for path in sorted(root.rglob("*.py"))
            if "__pycache__" not in path.parts
        )
    return paths


def _private_public_helper_paths() -> list[str]:
    paths: list[str] = []
    for root_name in PUBLIC_ROOTS:
        root = PACKAGE_ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts or path.name == "__init__.py":
                continue
            relative_parts = path.relative_to(root).parts
            has_private_part = any(part.startswith("_") for part in relative_parts)
            if has_private_part:
                paths.append(_relative_package_path(path))
    return paths


def test_api_index_keeps_internal_pages_out_of_main_guide() -> None:
    text = (ROOT / "docs/api/index.md").read_text(encoding="utf-8")

    assert "\ncore\n" not in text
    assert "\nmath\n" not in text
    assert "\ncalc\n" not in text
    assert "\nadapters\n" not in text
    assert "Retired public namespaces are intentionally absent from this guide." not in text


def test_old_runtime_storage_and_internal_api_pages_are_removed() -> None:
    for relative_path in (
        "docs/api/calc.md",
        "docs/api/adapters.md",
        "docs/api/core.md",
        "docs/api/math.md",
    ):
        assert not (ROOT / relative_path).exists(), f"{relative_path} must not be a public API doc"


def test_dev_internal_modules_page_documents_non_public_modules() -> None:
    text = _dev_internal_docs_text()

    assert "# Developer Internal Modules" in text
    assert "not public API" in text
    assert "docs/api/index.md" not in text
    assert "../api/index.md" in text

    for internal_root in (
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py._runtime",
        "fuggers_py._storage",
    ):
        assert internal_root in text

    for heading in (
        "## Public Boundary",
        "## Ownership Rules",
        "## Import Rules",
        "## Error Rules",
        "## Type And Value Rules",
        "## Numerical Rules",
        "## Runtime And Storage Rules",
        "## Testing And Docs Rules",
        "## Internal Root Inventory",
        "## Private Helpers Inside Public Packages",
        "## Change Checklist",
    ):
        assert heading in text


def test_dev_internal_modules_page_lists_every_internal_root_module() -> None:
    text = _dev_internal_docs_text()

    for relative_path in _internal_root_python_paths():
        assert f"`{relative_path}`" in text, f"{relative_path} is missing from internal module docs"


def test_dev_internal_modules_page_lists_private_helpers_inside_public_packages() -> None:
    text = _dev_internal_docs_text()

    for relative_path in _private_public_helper_paths():
        assert f"`{relative_path}`" in text, f"{relative_path} is missing from internal module docs"


def test_dev_internal_modules_page_does_not_teach_deep_private_public_imports() -> None:
    text = _dev_internal_docs_text()

    forbidden = (
        "fuggers_py.bonds._",
        "fuggers_py.curves._",
        "fuggers_py.portfolio._",
        "fuggers_py.rates._",
    )
    for forbidden_text in forbidden:
        assert forbidden_text not in text


def test_project_docs_link_dev_internal_modules() -> None:
    text = (ROOT / "docs/index.md").read_text(encoding="utf-8")

    assert "dev/internal_modules" in text


def test_module_reference_page_is_archived_and_readme_does_not_call_it_live_inventory() -> None:
    module_reference_text = (ROOT / "docs/MODULE_REFERENCE.md").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Archived note." in module_reference_text
    assert "no longer the live source-tree inventory" in module_reference_text
    assert "SRC_STRUCTURE.md" in module_reference_text
    assert "docs/api/index.md" in module_reference_text
    assert "live source tree" not in readme_text
