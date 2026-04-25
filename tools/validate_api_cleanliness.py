from __future__ import annotations

import argparse
import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_API_ROOTS = {
    "bonds",
    "credit",
    "curves",
    "funding",
    "inflation",
    "portfolio",
    "rates",
    "vol_surfaces",
}

LEGACY_PUBLIC_ROOTS = {
    "adapters",
    "calc",
    "core",
    "market",
    "market_curves",
    "math",
    "measures",
    "pricers",
    "products",
    "reference",
}

LEGACY_PRIVATE_ROOTS = {
    "_adapters",
    "_calc",
    "_market",
    "_measures",
    "_pricers",
    "_products",
    "_reference",
}

LEGACY_IMPORT_PREFIXES = {
    *(f"fuggers_py.{root}" for root in LEGACY_PUBLIC_ROOTS),
    *(f"fuggers_py.{root}" for root in LEGACY_PRIVATE_ROOTS),
    "fuggers_py._inflation_types",
}


@dataclass(frozen=True, slots=True)
class CleanlinessResult:
    ok: bool
    errors: list[str]

    @property
    def reason(self) -> str | None:
        if self.ok:
            return None
        return self.errors[0]


def _run_shell(root: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_output(root: Path, command: list[str]) -> list[str]:
    completed = _run_shell(root, command)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _git_failure_message(action: str, completed: subprocess.CompletedProcess[str]) -> str:
    detail = (completed.stderr or completed.stdout).strip()
    if detail:
        return f"{action}: {detail}"
    return action


def _git_available(root: Path) -> bool:
    completed = _run_shell(root, ["git", "rev-parse", "--show-toplevel"])
    return completed.returncode == 0


def _current_changed_paths(root: Path) -> set[str]:
    if not _git_available(root):
        return set()
    changed = set(_git_output(root, ["git", "diff", "--name-only", "--relative", "HEAD"]))
    changed.update(_git_output(root, ["git", "diff", "--name-only", "--relative", "--cached", "HEAD"]))
    changed.update(_git_output(root, ["git", "ls-files", "--others", "--exclude-standard"]))
    return changed


def _changed_paths_from_base(root: Path, base_ref: str) -> set[str]:
    if not _git_available(root):
        raise ValueError("Cannot compare API cleanliness against a base ref outside a git repository.")

    completed = _run_shell(root, ["git", "diff", "--name-only", "--relative", f"{base_ref}...HEAD"])
    if completed.returncode != 0:
        raise ValueError(
            _git_failure_message(f"Cannot compare API cleanliness against base ref `{base_ref}`", completed)
        )
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def _all_source_paths(root: Path) -> set[str]:
    source_root = root / "src" / "fuggers_py"
    if not source_root.exists():
        return set()
    return {
        path.relative_to(root).as_posix()
        for path in source_root.rglob("*.py")
        if "__pycache__" not in path.parts
    }


def _is_source_path(path_text: str) -> bool:
    return path_text.startswith("src/fuggers_py/") and path_text.endswith(".py")


def _top_level_package(path_text: str) -> str | None:
    parts = Path(path_text).parts
    if len(parts) < 3 or parts[0] != "src" or parts[1] != "fuggers_py":
        return None
    if len(parts) == 3:
        return ""
    return parts[2]


def _is_public_source_path(path_text: str) -> bool:
    top_level = _top_level_package(path_text)
    return top_level == "" or top_level in PUBLIC_API_ROOTS


def _source_module_name(path_text: str) -> str | None:
    if not _is_source_path(path_text):
        return None
    relative = Path(path_text).relative_to("src")
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_import_from_module(path_text: str, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module

    module_name = _source_module_name(path_text)
    if module_name is None:
        return None
    path = Path(path_text)
    current_package = module_name if path.name == "__init__.py" else module_name.rpartition(".")[0]
    package_parts = current_package.split(".") if current_package else []
    if node.level > len(package_parts):
        return None
    base_parts = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(part for part in base_parts if part)


def _matches_prefix(module_name: str, prefixes: Iterable[str]) -> bool:
    return any(module_name == prefix or module_name.startswith(f"{prefix}.") for prefix in prefixes)


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def _module_file_errors(root: Path, path_text: str) -> list[str]:
    path = root / path_text
    if not path.exists():
        return []

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path_text)
    except SyntaxError as exc:
        return [f"{path_text} cannot be parsed: {exc.msg} at line {exc.lineno}."]

    errors: list[str] = []
    public_source = _is_public_source_path(path_text)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _matches_prefix(alias.name, LEGACY_IMPORT_PREFIXES):
                    errors.append(
                        f"{path_text}:{node.lineno} imports legacy API path `{alias.name}`. "
                        "Use the current first-layer public module or move the implementation."
                    )

        elif isinstance(node, ast.ImportFrom):
            imported_module = _resolve_import_from_module(path_text, node)
            if imported_module and _matches_prefix(imported_module, LEGACY_IMPORT_PREFIXES):
                errors.append(
                    f"{path_text}:{node.lineno} imports legacy API path `{imported_module}`. "
                    "Use the current first-layer public module or move the implementation."
                )
            if public_source and any(alias.name == "*" for alias in node.names):
                errors.append(
                    f"{path_text}:{node.lineno} uses a star import. "
                    "List the public names explicitly so the API surface stays readable."
                )

        elif public_source and isinstance(node, ast.Attribute) and _dotted_name(node) == "sys.modules":
            errors.append(
                f"{path_text}:{getattr(node, 'lineno', 1)} touches `sys.modules`. "
                "Do not keep old import paths alive with module aliases."
            )

        elif public_source and isinstance(node, ast.Call):
            function_name = _dotted_name(node.func)
            if function_name == "importlib.import_module":
                errors.append(
                    f"{path_text}:{node.lineno} calls `importlib.import_module`. "
                    "Public modules should import their API directly instead of loading compatibility paths dynamically."
                )

    return errors


def _path_namespace_errors(root: Path, path_text: str) -> list[str]:
    if not _is_source_path(path_text):
        return []
    path = root / path_text
    if not path.exists():
        return []

    top_level = _top_level_package(path_text)
    if top_level in LEGACY_PUBLIC_ROOTS:
        return [
            f"{path_text} revives old public namespace `fuggers_py.{top_level}`. "
            "Use the current first-layer public modules instead."
        ]
    if top_level in LEGACY_PRIVATE_ROOTS:
        return [
            f"{path_text} revives old private namespace `fuggers_py.{top_level}`. "
            "Move the implementation under the current package owner instead."
        ]
    return []


def validate_api_cleanliness(
    root: Path,
    *,
    paths: set[str] | None = None,
    all_files: bool = False,
    base_ref: str | None = None,
) -> CleanlinessResult:
    try:
        if all_files:
            candidate_paths = _all_source_paths(root)
        elif paths is not None:
            candidate_paths = paths
        elif base_ref is not None:
            candidate_paths = _changed_paths_from_base(root, base_ref)
        else:
            candidate_paths = _current_changed_paths(root)
    except ValueError as exc:
        return CleanlinessResult(ok=False, errors=[str(exc)])

    source_paths = sorted(path for path in candidate_paths if _is_source_path(path))

    errors: list[str] = []
    for path_text in source_paths:
        errors.extend(_path_namespace_errors(root, path_text))
        errors.extend(_module_file_errors(root, path_text))

    deduped_errors = list(dict.fromkeys(errors))
    return CleanlinessResult(ok=not deduped_errors, errors=deduped_errors)


def _format_failure(errors: list[str]) -> str:
    lines = ["API cleanliness failed.", ""]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check API cleanliness rules for changed source files.")
    parser.add_argument("--all", action="store_true", help="Check all source files instead of only changed files.")
    parser.add_argument(
        "--base-ref",
        help="Compare changed source files against this git ref instead of the local working tree.",
    )
    args = parser.parse_args(argv)
    if args.all and args.base_ref:
        parser.error("--base-ref cannot be used with --all.")

    result = validate_api_cleanliness(ROOT, all_files=args.all, base_ref=args.base_ref)
    if result.ok:
        print("PASS: API cleanliness gate passed.")
        return 0

    print(_format_failure(result.errors))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
