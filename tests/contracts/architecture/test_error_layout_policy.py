from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
PACKAGE_ROOT = ROOT / "src" / "fuggers_py"


def _module_name(path: Path) -> str:
    relative = path.relative_to(PACKAGE_ROOT).with_suffix("")
    return "fuggers_py." + ".".join(relative.parts)


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _error_module_paths() -> list[Path]:
    return sorted(path for path in PACKAGE_ROOT.rglob("errors.py") if "__pycache__" not in path.parts)


def _exception_base_names() -> set[str]:
    names = {"Exception"}
    for path in _error_module_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                names.add(node.name)
    return names


def test_library_exception_classes_live_in_error_modules() -> None:
    base_names = _exception_base_names()
    offenders: list[str] = []

    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "errors.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            inherited = {_base_name(base) for base in node.bases}
            if inherited & base_names:
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} {node.name}")

    assert offenders == []


def test_error_modules_share_the_fuggers_error_root() -> None:
    from fuggers_py._core.errors import FuggersError

    offenders: list[str] = []
    for path in _error_module_paths():
        module = importlib.import_module(_module_name(path))
        for _, value in vars(module).items():
            if not inspect.isclass(value):
                continue
            if value.__module__ != module.__name__:
                continue
            if not issubclass(value, Exception):
                continue
            if value is FuggersError:
                continue
            if not issubclass(value, FuggersError):
                offenders.append(f"{module.__name__}.{value.__name__}")

    assert offenders == []
