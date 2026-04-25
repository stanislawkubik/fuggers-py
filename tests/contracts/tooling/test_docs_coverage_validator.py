from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def _load_validator() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "validate_docs_coverage.py"
    spec = importlib.util.spec_from_file_location("validate_docs_coverage_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=root, check=True, capture_output=True, text=True)


def _git_commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, capture_output=True, text=True)


def _git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_public_api_surface_change_requires_api_docs() -> None:
    module = _load_validator()

    result = module.validate_docs_coverage(
        Path.cwd(),
        path_status={"specs/public_api_surface.json": "M"},
    )

    assert result.ok is False
    assert result.reason == (
        "specs/public_api_surface.json changed. Update the matching `docs/api/*.md` page for the public API change."
    )


def test_public_domain_init_change_requires_matching_domain_doc() -> None:
    module = _load_validator()

    result = module.validate_docs_coverage(
        Path.cwd(),
        path_status={"src/fuggers_py/rates/__init__.py": "M"},
    )

    assert result.ok is False
    assert result.reason == "fuggers_py.rates public API shape changed. Update `docs/api/rates.md`."


def test_public_domain_doc_satisfies_public_api_change() -> None:
    module = _load_validator()

    result = module.validate_docs_coverage(
        Path.cwd(),
        path_status={
            "src/fuggers_py/rates/__init__.py": "M",
            "docs/api/rates.md": "M",
        },
    )

    assert result.ok is True


def test_internal_module_shape_change_requires_internal_docs() -> None:
    module = _load_validator()

    result = module.validate_docs_coverage(
        Path.cwd(),
        path_status={"src/fuggers_py/_runtime/new_module.py": "A"},
    )

    assert result.ok is False
    assert result.errors == [
        "Source files were added, deleted, or renamed. Update `docs/SRC_STRUCTURE.md`.",
        "Internal source modules were added, deleted, or renamed. Update "
        "`docs/dev/internal_modules.md` or `docs/SRC_STRUCTURE.md`.",
    ]


def test_internal_docs_satisfy_internal_module_shape_change() -> None:
    module = _load_validator()

    result = module.validate_docs_coverage(
        Path.cwd(),
        path_status={
            "src/fuggers_py/_runtime/new_module.py": "A",
            "docs/SRC_STRUCTURE.md": "M",
        },
    )

    assert result.ok is True


def test_example_catalog_change_requires_examples_readme() -> None:
    module = _load_validator()

    result = module.validate_docs_coverage(
        Path.cwd(),
        path_status={"examples/02_new_workflow.ipynb": "A"},
    )

    assert result.ok is False
    assert result.reason == "Examples were added, deleted, or renamed. Update `examples/README.md`."


def test_tooling_change_requires_validation_docs() -> None:
    module = _load_validator()

    result = module.validate_docs_coverage(
        Path.cwd(),
        path_status={"tools/repo_hooks.py": "M"},
    )

    assert result.ok is False
    assert result.reason == (
        "Repo hook or validation tooling changed. Update `docs/validation_strategy.md` "
        "or `tests/README_add_feature_workflow.md`."
    )


def test_base_ref_checks_committed_pr_diff(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "src" / "fuggers_py" / "rates" / "__init__.py", "__all__ = []\n")
    _write_text(tmp_path / "docs" / "api" / "rates.md", "# Rates\n")
    _git_commit_all(tmp_path, "baseline")
    base_ref = _git_head(tmp_path)

    _write_text(tmp_path / "src" / "fuggers_py" / "rates" / "__init__.py", "__all__ = ['SwapPricer']\n")
    _git_commit_all(tmp_path, "change rates api")

    result = module.validate_docs_coverage(tmp_path, base_ref=base_ref)

    assert result.ok is False
    assert result.reason == "fuggers_py.rates public API shape changed. Update `docs/api/rates.md`."
