from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

from tests.helpers._paths import REPO_ROOT

ROOT = REPO_ROOT
PACKAGE_ROOT = REPO_ROOT / "src" / "fuggers_py"
EXPECTED_TOP_LEVEL_DIRS = {
    "_core",
    "_math",
    "_runtime",
    "_storage",
    "bonds",
    "credit",
    "curves",
    "funding",
    "inflation",
    "portfolio",
    "rates",
    "vol_surfaces",
}
REMOVED_TOP_LEVEL_DIRS = (
    "adapters",
    "calc",
    "core",
    "market",
    "math",
    "measures",
    "pricers",
    "products",
    "reference",
)
REMOVED_INTERNAL_BUCKETS = (
    "_products",
    "_pricers",
    "_measures",
    "_reference",
    "_market",
    "_calc",
    "_adapters",
)
REMOVED_NAMESPACE_ROOTS = (
    "analytics",
    "data",
    "engine",
    "io",
)
AUDIT_ROOTS = (
    ROOT / "src",
    ROOT / "tests",
    ROOT / "docs",
    ROOT / "examples",
    ROOT / ".github",
    ROOT / "tools",
    ROOT / "typecheck",
)
AUDIT_FILES = (
    ROOT / "README.md",
    ROOT / "pyproject.toml",
)
SKIP_SUFFIXES: Final = {".pyc", ".zip"}
CANONICAL_PUBLIC_DIRS: Final = ("curves", "vol_surfaces", "bonds", "rates", "inflation", "credit", "funding", "portfolio")
DIRECT_IMPORT_SURFACES: Final = (
    ("fuggers_py", PACKAGE_ROOT / "__init__.py"),
    ("fuggers_py.bonds", PACKAGE_ROOT / "bonds" / "__init__.py"),
    ("fuggers_py.rates", PACKAGE_ROOT / "rates" / "__init__.py"),
    ("fuggers_py.inflation", PACKAGE_ROOT / "inflation" / "__init__.py"),
    ("fuggers_py.credit", PACKAGE_ROOT / "credit" / "__init__.py"),
    ("fuggers_py.funding", PACKAGE_ROOT / "funding" / "__init__.py"),
    ("fuggers_py.curves", PACKAGE_ROOT / "curves" / "__init__.py"),
    ("fuggers_py.vol_surfaces", PACKAGE_ROOT / "vol_surfaces" / "__init__.py"),
    ("fuggers_py.portfolio", PACKAGE_ROOT / "portfolio" / "__init__.py"),
)


def _canonical_public_python_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = [("fuggers_py", PACKAGE_ROOT / "__init__.py")]
    for package_name in CANONICAL_PUBLIC_DIRS:
        package_dir = PACKAGE_ROOT / package_name
        files.extend(
            (f"fuggers_py.{package_name}", path)
            for path in sorted(package_dir.rglob("*.py"))
            if "__pycache__" not in path.parts
        )
    return files


def _direct_import_surface_files() -> list[tuple[str, Path]]:
    return [(package_name, path) for package_name, path in DIRECT_IMPORT_SURFACES if path.exists()]


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base_name = _dotted_name(node.value)
        if base_name is None:
            return None
        return f"{base_name}.{node.attr}"
    return None


def _lazy_routing_markers(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    markers: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__getattr__":
            markers.append("__getattr__")
        elif isinstance(node, ast.Call):
            func_name = _dotted_name(node.func)
            if func_name in {"import_module", "importlib.import_module", "__import__"}:
                markers.append(str(func_name))
        elif isinstance(node, ast.Attribute) and _dotted_name(node) == "sys.modules":
            markers.append("sys.modules")
    return sorted(set(markers))


def _module_reassignment_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "__module__":
                    lines.add(node.lineno)
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Attribute) and target.attr == "__module__":
                lines.add(node.lineno)
        elif isinstance(node, ast.Call):
            func_name = _dotted_name(node.func)
            if func_name != "setattr" or len(node.args) < 2:
                continue
            module_arg = node.args[1]
            if isinstance(module_arg, ast.Constant) and module_arg.value == "__module__":
                lines.add(node.lineno)
    return sorted(lines)


def test_top_level_package_tree_matches_final_policy() -> None:
    actual = {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }
    assert actual == EXPECTED_TOP_LEVEL_DIRS


def test_removed_root_directories_do_not_exist() -> None:
    assert all(not (PACKAGE_ROOT / root_name).exists() for root_name in REMOVED_TOP_LEVEL_DIRS)
    assert all(not (PACKAGE_ROOT / bucket_name).exists() for bucket_name in REMOVED_INTERNAL_BUCKETS)
    assert not (PACKAGE_ROOT / "_compat.py").exists()


def test_public_packages_do_not_keep_shadowed_module_files_next_to_packages() -> None:
    offenders: list[str] = []

    for package_name in CANONICAL_PUBLIC_DIRS:
        package_dir = PACKAGE_ROOT / package_name
        for child_dir in sorted(path for path in package_dir.iterdir() if path.is_dir() and path.name != "__pycache__"):
            shadow_file = package_dir / f"{child_dir.name}.py"
            if shadow_file.exists():
                offenders.append(str(shadow_file.relative_to(ROOT)))

    assert offenders == []


def test_repo_contains_no_removed_root_namespace_references() -> None:
    namespace_pattern = re.compile(rf"fuggers_py\.({'|'.join(REMOVED_NAMESPACE_ROOTS)})\b")
    offenders: list[str] = []

    for audit_root in AUDIT_ROOTS:
        if not audit_root.exists():
            continue
        for path in audit_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in SKIP_SUFFIXES:
                continue
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if namespace_pattern.search(text):
                offenders.append(str(path.relative_to(ROOT)))

    for path in AUDIT_FILES:
        if path.exists() and namespace_pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_canonical_public_python_files_do_not_use_lazy_export_routing() -> None:
    offenders: list[str] = []

    for package_name, path in _direct_import_surface_files():
        markers = _lazy_routing_markers(path)
        if markers:
            joined = ", ".join(markers)
            offenders.append(f"{package_name}:{path.relative_to(ROOT)}:{joined}")

    assert offenders == []


def test_canonical_public_python_files_do_not_reassign___module__() -> None:
    offenders: list[str] = []

    for package_name, path in _canonical_public_python_files():
        lines = _module_reassignment_lines(path)
        if lines:
            line_list = ", ".join(str(line) for line in lines)
            offenders.append(f"{package_name}:{path.relative_to(ROOT)}:{line_list}")

    assert offenders == []
