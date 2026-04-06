from __future__ import annotations

import re
from typing import Final

from tests.helpers._paths import REPO_ROOT

ROOT = REPO_ROOT
PACKAGE_ROOT = REPO_ROOT / "src" / "fuggers_py"
ALLOWED_TOP_LEVEL_DIRS = {
    "adapters",
    "calc",
    "core",
    "market",
    "math",
    "measures",
    "portfolio",
    "pricers",
    "products",
    "reference",
}
REMOVED_ROOTS = (
    "analytics",
    "bonds",
    "credit",
    "curves",
    "data",
    "engine",
    "funding",
    "inflation",
    "io",
    "rates",
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


def test_top_level_package_tree_matches_final_policy() -> None:
    actual = {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }
    assert actual == ALLOWED_TOP_LEVEL_DIRS


def test_removed_root_directories_do_not_exist() -> None:
    assert all(not (PACKAGE_ROOT / root_name).exists() for root_name in REMOVED_ROOTS)
    assert not (PACKAGE_ROOT / "_compat.py").exists()


def test_repo_contains_no_removed_root_namespace_references() -> None:
    namespace_pattern = re.compile(rf"fuggers_py\.({'|'.join(REMOVED_ROOTS)})\b")
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
