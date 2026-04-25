from __future__ import annotations

import argparse
import ast
from datetime import UTC, datetime
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SURFACE_PATH = Path("specs/public_api_surface.json")
INTENT_PATH = Path(".tmp/repo_hooks/public_api_surface_intent.json")
PUBLIC_MODULE_PATHS = {
    "fuggers_py": Path("src/fuggers_py/__init__.py"),
    "fuggers_py.bonds": Path("src/fuggers_py/bonds/__init__.py"),
    "fuggers_py.credit": Path("src/fuggers_py/credit/__init__.py"),
    "fuggers_py.curves": Path("src/fuggers_py/curves/__init__.py"),
    "fuggers_py.funding": Path("src/fuggers_py/funding/__init__.py"),
    "fuggers_py.inflation": Path("src/fuggers_py/inflation/__init__.py"),
    "fuggers_py.portfolio": Path("src/fuggers_py/portfolio/__init__.py"),
    "fuggers_py.rates": Path("src/fuggers_py/rates/__init__.py"),
    "fuggers_py.vol_surfaces": Path("src/fuggers_py/vol_surfaces/__init__.py"),
}


@dataclass(frozen=True, slots=True)
class SurfaceDiff:
    added: dict[str, list[str]]
    removed: dict[str, list[str]]

    @property
    def ok(self) -> bool:
        return not self.added and not self.removed


@dataclass(frozen=True, slots=True)
class SurfaceValidationResult:
    ok: bool
    errors: list[str]

    @property
    def reason(self) -> str | None:
        if self.ok:
            return None
        return self.errors[0]


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_shell(root: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_available(root: Path) -> bool:
    completed = _run_shell(root, ["git", "rev-parse", "--show-toplevel"])
    return completed.returncode == 0


def _git_failure_message(action: str, completed: subprocess.CompletedProcess[str]) -> str:
    detail = (completed.stderr or completed.stdout).strip()
    if detail:
        return f"{action}: {detail}"
    return action


def _surface_contract_tracked_in_head(root: Path) -> bool:
    if not _git_available(root):
        return False
    completed = _run_shell(root, ["git", "ls-files", "--error-unmatch", SURFACE_PATH.as_posix()])
    return completed.returncode == 0


def _surface_contract_changed_from_head(root: Path) -> bool:
    if not _surface_contract_tracked_in_head(root):
        return False
    completed = _run_shell(root, ["git", "diff", "--quiet", "HEAD", "--", SURFACE_PATH.as_posix()])
    return completed.returncode != 0


def _surface_contract_changed_from_base(root: Path, base_ref: str) -> bool:
    if not _git_available(root):
        raise ValueError(
            "Cannot compare public API surface contract permission against a base ref outside a git repository."
        )

    completed = _run_shell(
        root,
        ["git", "diff", "--name-only", "--relative", f"{base_ref}...HEAD", "--", SURFACE_PATH.as_posix()],
    )
    if completed.returncode != 0:
        raise ValueError(
            _git_failure_message(
                f"Cannot compare public API surface contract permission against base ref `{base_ref}`",
                completed,
            )
        )
    return any(line.strip() == SURFACE_PATH.as_posix() for line in completed.stdout.splitlines())


def _surface_contract_hash(root: Path) -> str:
    path = root / SURFACE_PATH
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_public_api_surface_intent(root: Path) -> dict[str, Any] | None:
    path = root / INTENT_PATH
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def write_public_api_surface_intent(root: Path, *, prompt: str) -> Path:
    path = root / INTENT_PATH
    _json_dump(
        path,
        {
            "active": True,
            "used": False,
            "created_at": _now_iso(),
            "prompt": prompt,
        },
    )
    return path


def _mark_public_api_surface_intent_used(root: Path) -> None:
    payload = _load_public_api_surface_intent(root) or {}
    payload["active"] = True
    payload["used"] = True
    payload["used_at"] = _now_iso()
    payload["surface_sha256"] = _surface_contract_hash(root)
    _json_dump(root / INTENT_PATH, payload)


def _public_api_surface_intent_allows_update(root: Path) -> bool:
    payload = _load_public_api_surface_intent(root)
    return bool(payload and payload.get("active") is True and payload.get("used") is not True)


def _public_api_surface_intent_matches_contract(root: Path) -> bool:
    payload = _load_public_api_surface_intent(root)
    if not payload or payload.get("active") is not True or payload.get("used") is not True:
        return False
    return payload.get("surface_sha256") == _surface_contract_hash(root)


def _surface_contract_matches_current_exports(root: Path) -> SurfaceValidationResult:
    try:
        expected = _load_expected_surface(root)
        current = build_current_surface(root)
    except ValueError as exc:
        return SurfaceValidationResult(ok=False, errors=[str(exc)])

    diff = diff_surfaces(expected, current)
    if diff.ok:
        return SurfaceValidationResult(ok=True, errors=[])

    errors: list[str] = [
        "specs/public_api_surface.json changed, but it does not match the current public `__all__` exports."
    ]
    for module_name, names in diff.added.items():
        for name in names:
            errors.append(f"Missing surface export: {module_name}.{name}")
    for module_name, names in diff.removed.items():
        for name in names:
            errors.append(f"Stale surface export: {module_name}.{name}")
    return SurfaceValidationResult(ok=False, errors=errors)


def _read_module_exports(root: Path, module_name: str, module_path: Path) -> list[str]:
    path = root / module_path
    if not path.exists():
        raise ValueError(f"{module_path.as_posix()} is missing.")

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=module_path.as_posix())
    exports_node: ast.AST | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
                exports_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "__all__":
            exports_node = node.value

    if exports_node is None:
        raise ValueError(f"{module_path.as_posix()} must define literal `__all__` for {module_name}.")

    try:
        exports = ast.literal_eval(exports_node)
    except (ValueError, SyntaxError) as exc:
        raise ValueError(f"{module_path.as_posix()} must define `__all__` as a literal list of strings.") from exc

    if not isinstance(exports, list) or not all(isinstance(name, str) and name for name in exports):
        raise ValueError(f"{module_path.as_posix()} must define `__all__` as a literal list of strings.")

    duplicates = sorted({name for name in exports if exports.count(name) > 1})
    if duplicates:
        raise ValueError(
            f"{module_path.as_posix()} has duplicate public exports: {', '.join(duplicates)}."
        )

    return sorted(exports)


def build_current_surface(root: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "modules": {
            module_name: {
                "exports": _read_module_exports(root, module_name, module_path),
            }
            for module_name, module_path in sorted(PUBLIC_MODULE_PATHS.items())
        },
    }


def write_current_surface(root: Path, *, output_path: Path | None = None) -> Path:
    path = root / (output_path or SURFACE_PATH)
    _json_dump(path, build_current_surface(root))
    return path


def update_public_api_surface(root: Path) -> Path:
    expected: dict[str, Any] | None
    try:
        expected = _load_expected_surface(root)
    except ValueError:
        expected = None

    current = build_current_surface(root)
    surface_changes = expected is None or not diff_surfaces(expected, current).ok
    requires_intent = surface_changes and _surface_contract_tracked_in_head(root)
    if requires_intent and not _public_api_surface_intent_allows_update(root):
        raise ValueError(
            "Updating specs/public_api_surface.json requires an explicit user prompt such as "
            "`update public API surface` or `accept public API change`."
        )

    path = root / SURFACE_PATH
    _json_dump(path, current)
    if requires_intent:
        _mark_public_api_surface_intent_used(root)
    return path


def _load_expected_surface(root: Path) -> dict[str, Any]:
    path = root / SURFACE_PATH
    if not path.exists():
        raise ValueError(
            f"{SURFACE_PATH.as_posix()} is missing. Run `python tools/update_public_api_surface.py`."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"{SURFACE_PATH.as_posix()} must have `schema_version` 1.")
    modules = payload.get("modules")
    if not isinstance(modules, dict):
        raise ValueError(f"{SURFACE_PATH.as_posix()} must contain a `modules` object.")
    return payload


def diff_surfaces(expected: dict[str, Any], current: dict[str, Any]) -> SurfaceDiff:
    expected_modules = expected["modules"]
    current_modules = current["modules"]
    added: dict[str, list[str]] = {}
    removed: dict[str, list[str]] = {}

    for module_name in sorted(set(expected_modules) | set(current_modules)):
        expected_exports = set(expected_modules.get(module_name, {}).get("exports", []))
        current_exports = set(current_modules.get(module_name, {}).get("exports", []))
        module_added = sorted(current_exports - expected_exports)
        module_removed = sorted(expected_exports - current_exports)
        if module_added:
            added[module_name] = module_added
        if module_removed:
            removed[module_name] = module_removed

    return SurfaceDiff(added=added, removed=removed)


def validate_public_api_surface(root: Path) -> SurfaceValidationResult:
    try:
        expected = _load_expected_surface(root)
        current = build_current_surface(root)
    except ValueError as exc:
        return SurfaceValidationResult(ok=False, errors=[str(exc)])

    diff = diff_surfaces(expected, current)
    if diff.ok:
        return SurfaceValidationResult(ok=True, errors=[])

    errors: list[str] = []
    for module_name, names in diff.added.items():
        for name in names:
            errors.append(f"Added public export: {module_name}.{name}")
    for module_name, names in diff.removed.items():
        for name in names:
            errors.append(f"Removed public export: {module_name}.{name}")

    return SurfaceValidationResult(ok=False, errors=errors)


def validate_public_api_surface_contract_permission(
    root: Path,
    *,
    base_ref: str | None = None,
) -> SurfaceValidationResult:
    try:
        contract_changed = (
            _surface_contract_changed_from_base(root, base_ref)
            if base_ref is not None
            else _surface_contract_changed_from_head(root)
        )
    except ValueError as exc:
        return SurfaceValidationResult(ok=False, errors=[str(exc)])

    if not contract_changed:
        return SurfaceValidationResult(ok=True, errors=[])
    if base_ref is not None:
        return _surface_contract_matches_current_exports(root)
    if _public_api_surface_intent_matches_contract(root):
        return SurfaceValidationResult(ok=True, errors=[])
    return SurfaceValidationResult(
        ok=False,
        errors=[
            "specs/public_api_surface.json changed without an allowed public API surface update. "
            "Ask explicitly to update the public API surface, then run `python tools/update_public_api_surface.py`.",
        ],
    )


def _format_failure(errors: list[str]) -> str:
    lines = [
        "Public API surface changed.",
        "",
        *[f"- {error}" for error in errors],
        "",
        "If this public API change is intended, run:",
        "python tools/update_public_api_surface.py",
        "",
        "Then update the matching API tests and docs.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the committed public API surface.")
    parser.add_argument(
        "--check-contract-permission",
        action="store_true",
        help="Check that changes to specs/public_api_surface.json used an explicit prompt permission.",
    )
    parser.add_argument(
        "--base-ref",
        help="Compare contract changes against this git ref instead of the local working tree.",
    )
    args = parser.parse_args(argv)

    if args.check_contract_permission:
        result = validate_public_api_surface_contract_permission(ROOT, base_ref=args.base_ref)
        if result.ok:
            print("PASS: public API surface contract update permission is valid.")
            return 0
        print(_format_failure(result.errors))
        return 1

    result = validate_public_api_surface(ROOT)
    if result.ok:
        print("PASS: public API surface matches specs/public_api_surface.json.")
        return 0

    print(_format_failure(result.errors))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
