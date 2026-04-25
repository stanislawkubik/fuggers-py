from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_hooks() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "repo_hooks.py"
    tools_path = str(repo_root / "tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    spec = importlib.util.spec_from_file_location("repo_hooks_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _completed(command: list[str] | str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, 0, "", "")


class _Result:
    def __init__(self, *, ok: bool = True, errors: list[str] | None = None) -> None:
        self.ok = ok
        self.errors = errors or []

    @property
    def reason(self) -> str | None:
        return None if self.ok else self.errors[0]


def test_user_prompt_hook_always_injects_general_repo_standards(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_hooks()

    monkeypatch.setattr(module, "_write_turn_state", lambda prompt: None)
    monkeypatch.setattr(module, "_run_add_feature_hook", lambda command, raw_stdin: _completed(command))

    assert module.handle_user_prompt_hook('{"prompt": "Edit one example notebook."}') == 0


def test_stop_hook_skips_api_gates_for_example_only_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_hooks()
    api_calls: list[str] = []

    monkeypatch.setattr(module, "_run_add_feature_hook", lambda command, raw_stdin: _completed(command))
    monkeypatch.setattr(module, "_turn_changed_paths", lambda: {"examples/01_treasury_curve_fit.ipynb"})
    monkeypatch.setattr(module, "_turn_path_status", lambda paths: {"examples/01_treasury_curve_fit.ipynb": "M"})
    monkeypatch.setattr(module, "validate_docs_coverage", lambda root, *, path_status: _Result())
    monkeypatch.setattr(
        module,
        "validate_api_cleanliness",
        lambda root, *, paths: api_calls.append("api_cleanliness") or _Result(),
    )
    monkeypatch.setattr(
        module,
        "validate_public_api_surface",
        lambda root: api_calls.append("api_surface") or _Result(),
    )

    assert module.handle_stop_hook("{}") == 0

    assert api_calls == []


def test_stop_hook_runs_global_api_gates_for_source_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_hooks()
    calls: list[str] = []

    monkeypatch.setattr(module, "_run_add_feature_hook", lambda command, raw_stdin: _completed(command))
    monkeypatch.setattr(module, "_turn_changed_paths", lambda: {"src/fuggers_py/curves/base.py"})
    monkeypatch.setattr(module, "_turn_path_status", lambda paths: {"src/fuggers_py/curves/base.py": "M"})
    monkeypatch.setattr(module, "validate_docs_coverage", lambda root, *, path_status: calls.append("docs") or _Result())
    monkeypatch.setattr(
        module,
        "validate_api_cleanliness",
        lambda root, *, paths: calls.append("api_cleanliness") or _Result(),
    )
    monkeypatch.setattr(
        module,
        "validate_public_api_surface",
        lambda root: calls.append("api_surface") or _Result(),
    )

    assert module.handle_stop_hook("{}") == 0

    assert calls == ["docs", "api_cleanliness"]


def test_stop_hook_runs_surface_gate_for_public_api_files(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_hooks()
    calls: list[str] = []

    monkeypatch.setattr(module, "_run_add_feature_hook", lambda command, raw_stdin: _completed(command))
    monkeypatch.setattr(module, "_turn_changed_paths", lambda: {"src/fuggers_py/rates/__init__.py"})
    monkeypatch.setattr(module, "_turn_path_status", lambda paths: {"src/fuggers_py/rates/__init__.py": "M"})
    monkeypatch.setattr(module, "validate_docs_coverage", lambda root, *, path_status: calls.append("docs") or _Result())
    monkeypatch.setattr(
        module,
        "validate_api_cleanliness",
        lambda root, *, paths: calls.append("api_cleanliness") or _Result(),
    )
    monkeypatch.setattr(module, "validate_public_api_surface", lambda root: calls.append("api_surface") or _Result())
    monkeypatch.setattr(
        module,
        "validate_public_api_surface_contract_permission",
        lambda root: calls.append("surface_permission") or _Result(),
    )

    assert module.handle_stop_hook("{}") == 0

    assert calls == ["docs", "api_cleanliness", "api_surface", "surface_permission"]


def test_turn_changed_paths_ignore_pre_existing_dirty_files(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_hooks()

    monkeypatch.setattr(
        module,
        "_read_turn_state",
        lambda: {"changed_snapshot": {"src/fuggers_py/curves/base.py": "old-src"}},
    )
    monkeypatch.setattr(
        module,
        "_current_changed_snapshot",
        lambda: {
            "src/fuggers_py/curves/base.py": "old-src",
            "examples/01_treasury_curve_fit.ipynb": "new-example",
        },
    )

    assert module._turn_changed_paths() == {"examples/01_treasury_curve_fit.ipynb"}


def test_turn_path_status_marks_pre_existing_dirty_file_as_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_hooks()

    monkeypatch.setattr(
        module,
        "_read_turn_state",
        lambda: {"changed_snapshot": {"examples/01_treasury_curve_fit.ipynb": "old-example"}},
    )
    monkeypatch.setattr(
        module,
        "_current_path_status",
        lambda: {"examples/01_treasury_curve_fit.ipynb": "A"},
    )
    monkeypatch.setattr(module, "_path_fingerprint", lambda path: "new-example")

    assert module._turn_path_status({"examples/01_treasury_curve_fit.ipynb"}) == {
        "examples/01_treasury_curve_fit.ipynb": "M"
    }
