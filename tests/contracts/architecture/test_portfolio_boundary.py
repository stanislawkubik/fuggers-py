from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
PACKAGE_ROOT = ROOT / "src" / "fuggers_py"
PORTFOLIO_ROOT = PACKAGE_ROOT / "portfolio"
PUBLIC_PACKAGE_ROOTS = (
    "bonds",
    "credit",
    "curves",
    "funding",
    "inflation",
    "rates",
    "vol_surfaces",
)
FORBIDDEN_PORTFOLIO_DEPENDENCIES = (
    "fuggers_py._products",
    "fuggers_py._pricers",
    "fuggers_py._measures",
    "fuggers_py._market",
    "fuggers_py._reference",
    "fuggers_py._calc",
    "fuggers_py._runtime",
    "fuggers_py._storage",
    "fuggers_py._storage",
)
PORTFOLIO_PACKAGE = "fuggers_py.portfolio"


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _is_under(module: str, root: str) -> bool:
    return module == root or module.startswith(f"{root}.")


def _current_package_parts(path: Path) -> tuple[str, ...]:
    relative = path.relative_to(PACKAGE_ROOT).with_suffix("")
    parts = relative.parts
    if path.name == "__init__.py":
        return parts[:-1]
    return parts[:-1]


def _resolve_import_from(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module

    package_parts = _current_package_parts(path)
    keep_count = max(0, len(package_parts) - (node.level - 1))
    resolved = ["fuggers_py", *package_parts[:keep_count]]
    if node.module:
        resolved.extend(node.module.split("."))
    return ".".join(resolved)


def _imported_modules(path: Path, tree: ast.AST) -> list[tuple[int, str]]:
    modules: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_from(path, node)
            if module is not None:
                modules.append((node.lineno, module))
                modules.extend(
                    (node.lineno, f"{module}.{alias.name}")
                    for alias in node.names
                    if alias.name != "*"
                )

    return modules


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def _dynamic_import_strings(tree: ast.AST) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_name = _dotted_name(node.func)
        if function_name not in {"import_module", "importlib.import_module", "__import__"}:
            continue
        if not node.args:
            continue
        module_arg = node.args[0]
        if isinstance(module_arg, ast.Constant) and isinstance(module_arg.value, str):
            imports.append((node.lineno, module_arg.value))

    return imports


def _string_literals(tree: ast.AST) -> list[tuple[int, str]]:
    literals: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append((node.lineno, node.value))

    return literals


def _module_reference_offenders(path: Path, forbidden_roots: tuple[str, ...]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []

    for line, module in _imported_modules(path, tree):
        if any(_is_under(module, root) for root in forbidden_roots):
            offenders.append(f"{path.relative_to(ROOT)}:{line}: imports {module}")

    for line, module in _dynamic_import_strings(tree):
        if any(_is_under(module, root) for root in forbidden_roots):
            offenders.append(f"{path.relative_to(ROOT)}:{line}: dynamically imports {module}")

    for line, value in _string_literals(tree):
        for root in forbidden_roots:
            if root in value:
                offenders.append(f"{path.relative_to(ROOT)}:{line}: references {root!r} in a string")

    return offenders


def test_portfolio_files_do_not_depend_on_old_implementation_buckets() -> None:
    offenders: list[str] = []

    for path in _python_files(PORTFOLIO_ROOT):
        offenders.extend(_module_reference_offenders(path, FORBIDDEN_PORTFOLIO_DEPENDENCIES))

    assert offenders == []


def test_public_domain_packages_do_not_depend_on_portfolio() -> None:
    offenders: list[str] = []

    for package_name in PUBLIC_PACKAGE_ROOTS:
        for path in _python_files(PACKAGE_ROOT / package_name):
            offenders.extend(_module_reference_offenders(path, (PORTFOLIO_PACKAGE,)))

    assert offenders == []
