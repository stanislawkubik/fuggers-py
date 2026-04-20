from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
SRC = ROOT / "src" / "fuggers_py"
INWARD_LAYERS = (
    "core",
    "_reference",
    "_market",
    "_products",
    "_pricers",
    "_measures",
    "math",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _python_files(package_name: str) -> list[Path]:
    return sorted(path for path in (SRC / package_name).rglob("*.py") if "__pycache__" not in path.parts)


def test_inward_layers_do_not_depend_on_calc() -> None:
    offending: list[str] = []
    for package_name in INWARD_LAYERS:
        for path in _python_files(package_name):
            modules = _imported_modules(path)
            if any(module == "fuggers_py._calc" or module.startswith("fuggers_py._calc.") for module in modules):
                offending.append(str(path.relative_to(ROOT)))
    assert offending == []


def test_products_do_not_import_pricers_or_measures() -> None:
    offending: list[str] = []
    for path in _python_files("_products"):
        modules = _imported_modules(path)
        if any(
            module == "fuggers_py._pricers"
            or module.startswith("fuggers_py._pricers.")
            or module == "fuggers_py._measures"
            or module.startswith("fuggers_py._measures.")
            for module in modules
        ):
            offending.append(str(path.relative_to(ROOT)))
    assert offending == []


def test_reference_does_not_import_calc_or_portfolio() -> None:
    offending: list[str] = []
    for path in _python_files("_reference"):
        modules = _imported_modules(path)
        if any(
            module == "fuggers_py._calc"
            or module.startswith("fuggers_py._calc.")
            or module == "fuggers_py.portfolio"
            or module.startswith("fuggers_py.portfolio.")
            for module in modules
        ):
            offending.append(str(path.relative_to(ROOT)))
    assert offending == []
