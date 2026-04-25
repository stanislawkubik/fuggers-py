from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_API_DOCS = {
    "": "docs/api/index.md",
    "bonds": "docs/api/bonds.md",
    "credit": "docs/api/credit.md",
    "curves": "docs/api/curves.md",
    "funding": "docs/api/funding.md",
    "inflation": "docs/api/inflation.md",
    "portfolio": "docs/api/portfolio.md",
    "rates": "docs/api/rates.md",
    "vol_surfaces": "docs/api/vol_surfaces.md",
}
PUBLIC_ROOTS = set(PUBLIC_API_DOCS) - {""}
INTERNAL_ROOTS = {
    "_adapters",
    "_calc",
    "_core",
    "_inflation_types",
    "_market",
    "_math",
    "_measures",
    "_pricers",
    "_products",
    "_reference",
    "_runtime",
    "_storage",
}
INTERNAL_DOCS = {
    "docs/dev/internal_modules.md",
    "docs/SRC_STRUCTURE.md",
}
SOURCE_STRUCTURE_DOCS = {
    "docs/SRC_STRUCTURE.md",
}
TOOLING_DOCS = {
    "docs/validation_strategy.md",
    "tests/README_add_feature_workflow.md",
}
EXAMPLE_CATALOG_DOCS = {
    "examples/README.md",
}


@dataclass(frozen=True, slots=True)
class DocsCoverageResult:
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


def _git_available(root: Path) -> bool:
    completed = _run_shell(root, ["git", "rev-parse", "--show-toplevel"])
    return completed.returncode == 0


def _git_failure_message(action: str, completed: subprocess.CompletedProcess[str]) -> str:
    detail = (completed.stderr or completed.stdout).strip()
    if detail:
        return f"{action}: {detail}"
    return action


def _parse_name_status(output: str) -> dict[str, str]:
    changed: dict[str, str] = {}
    for raw_line in output.splitlines():
        parts = raw_line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            changed[parts[1]] = "D"
            changed[parts[2]] = "A"
        elif status.startswith("C") and len(parts) >= 3:
            changed[parts[2]] = "A"
        elif len(parts) >= 2:
            changed[parts[1]] = status[:1]
    return changed


def _git_name_status(root: Path, *, base_ref: str | None = None) -> dict[str, str]:
    if not _git_available(root):
        if base_ref is not None:
            raise ValueError("Cannot compare docs coverage against a base ref outside a git repository.")
        return {}

    if base_ref is not None:
        completed = _run_shell(root, ["git", "diff", "--name-status", "--relative", f"{base_ref}...HEAD"])
        if completed.returncode != 0:
            raise ValueError(
                _git_failure_message(f"Cannot compare docs coverage against base ref `{base_ref}`", completed)
            )
        return _parse_name_status(completed.stdout)

    completed = _run_shell(root, ["git", "diff", "--name-status", "--relative", "HEAD"])
    changed = _parse_name_status(completed.stdout) if completed.returncode == 0 else {}

    untracked = _run_shell(root, ["git", "ls-files", "--others", "--exclude-standard"])
    if untracked.returncode == 0:
        for raw_line in untracked.stdout.splitlines():
            path = raw_line.strip()
            if path:
                changed.setdefault(path, "A")

    return changed


def _is_live_doc_update(path_status: dict[str, str], paths: set[str]) -> bool:
    return any(path_status.get(path) not in {None, "D"} for path in paths)


def _top_level_package(path_text: str) -> str | None:
    parts = Path(path_text).parts
    if len(parts) < 3 or parts[0] != "src" or parts[1] != "fuggers_py":
        return None
    if len(parts) == 3:
        return ""
    return parts[2]


def _is_source_file(path_text: str) -> bool:
    return path_text.startswith("src/fuggers_py/") and path_text.endswith(".py")


def _is_shape_change(status: str) -> bool:
    return status in {"A", "D", "R"}


def _public_api_doc_requirements(path_status: dict[str, str]) -> list[str]:
    errors: list[str] = []
    docs_api_changed = any(
        path.startswith("docs/api/") and path.endswith(".md") and status != "D"
        for path, status in path_status.items()
    )

    if "specs/public_api_surface.json" in path_status and not docs_api_changed:
        errors.append(
            "specs/public_api_surface.json changed. Update the matching `docs/api/*.md` page for the public API change."
        )

    required_docs_by_root: dict[str, set[str]] = {}
    for path, status in path_status.items():
        if not _is_source_file(path):
            continue
        top_level = _top_level_package(path)
        if top_level not in PUBLIC_API_DOCS:
            continue
        is_public_init = path == "src/fuggers_py/__init__.py" or path == f"src/fuggers_py/{top_level}/__init__.py"
        if is_public_init or _is_shape_change(status):
            required_docs_by_root.setdefault(top_level or "", set()).add(PUBLIC_API_DOCS[top_level or ""])

    for top_level, docs in sorted(required_docs_by_root.items()):
        if not _is_live_doc_update(path_status, docs):
            module_name = "fuggers_py" if top_level == "" else f"fuggers_py.{top_level}"
            docs_text = " or ".join(f"`{path}`" for path in sorted(docs))
            errors.append(f"{module_name} public API shape changed. Update {docs_text}.")

    return errors


def _source_structure_requirements(path_status: dict[str, str]) -> list[str]:
    if any(_is_source_file(path) and _is_shape_change(status) for path, status in path_status.items()):
        if not _is_live_doc_update(path_status, SOURCE_STRUCTURE_DOCS):
            return ["Source files were added, deleted, or renamed. Update `docs/SRC_STRUCTURE.md`."]
    return []


def _internal_docs_requirements(path_status: dict[str, str]) -> list[str]:
    internal_shape_changed = any(
        _is_source_file(path)
        and _is_shape_change(status)
        and (_top_level_package(path) in INTERNAL_ROOTS or (_top_level_package(path) or "").startswith("_"))
        for path, status in path_status.items()
    )
    if internal_shape_changed and not _is_live_doc_update(path_status, INTERNAL_DOCS):
        return [
            "Internal source modules were added, deleted, or renamed. Update "
            "`docs/dev/internal_modules.md` or `docs/SRC_STRUCTURE.md`."
        ]
    return []


def _examples_requirements(path_status: dict[str, str]) -> list[str]:
    example_catalog_changed = any(
        path.startswith("examples/")
        and status in {"A", "D", "R"}
        and (path.endswith(".ipynb") or path.startswith("examples/synthetic_data/"))
        for path, status in path_status.items()
    )
    if example_catalog_changed and not _is_live_doc_update(path_status, EXAMPLE_CATALOG_DOCS):
        return ["Examples were added, deleted, or renamed. Update `examples/README.md`."]
    return []


def _docs_index_requirements(path_status: dict[str, str]) -> list[str]:
    api_doc_shape_changed = any(
        path.startswith("docs/api/") and path.endswith(".md") and status in {"A", "D", "R"}
        for path, status in path_status.items()
    )
    if api_doc_shape_changed and path_status.get("docs/api/index.md") in {None, "D"}:
        return ["API doc pages were added, deleted, or renamed. Update `docs/api/index.md`."]
    return []


def _tooling_docs_requirements(path_status: dict[str, str]) -> list[str]:
    tooling_changed = any(
        path == ".codex/hooks.json"
        or path == "tools/repo_hooks.py"
        or path.startswith("tools/validate_")
        or path.startswith("tools/update_public_api_surface.py")
        for path in path_status
    )
    if tooling_changed and not _is_live_doc_update(path_status, TOOLING_DOCS):
        return [
            "Repo hook or validation tooling changed. Update `docs/validation_strategy.md` "
            "or `tests/README_add_feature_workflow.md`."
        ]
    return []


def validate_docs_coverage(
    root: Path,
    *,
    path_status: dict[str, str] | None = None,
    base_ref: str | None = None,
) -> DocsCoverageResult:
    try:
        changed = path_status if path_status is not None else _git_name_status(root, base_ref=base_ref)
    except ValueError as exc:
        return DocsCoverageResult(ok=False, errors=[str(exc)])

    errors: list[str] = []
    errors.extend(_public_api_doc_requirements(changed))
    errors.extend(_source_structure_requirements(changed))
    errors.extend(_internal_docs_requirements(changed))
    errors.extend(_examples_requirements(changed))
    errors.extend(_docs_index_requirements(changed))
    errors.extend(_tooling_docs_requirements(changed))
    deduped_errors = list(dict.fromkeys(errors))
    return DocsCoverageResult(ok=not deduped_errors, errors=deduped_errors)


def _format_failure(errors: list[str]) -> str:
    lines = ["Docs coverage failed.", ""]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that structural and public API changes update matching docs.")
    parser.add_argument(
        "--base-ref",
        help="Compare changed paths against this git ref instead of the local working tree.",
    )
    args = parser.parse_args(argv)

    result = validate_docs_coverage(ROOT, base_ref=args.base_ref)
    if result.ok:
        print("PASS: docs coverage gate passed.")
        return 0

    print(_format_failure(result.errors))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
