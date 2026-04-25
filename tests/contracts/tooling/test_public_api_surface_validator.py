from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def _load_validator() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "validate_public_api_surface.py"
    spec = importlib.util.spec_from_file_location("validate_public_api_surface_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_public_modules(root: Path, *, rates_exports: list[str]) -> None:
    for module_name, module_path in _load_validator().PUBLIC_MODULE_PATHS.items():
        exports = rates_exports if module_name == "fuggers_py.rates" else []
        _write_text(
            root / module_path,
            "__all__ = " + repr(exports) + "\n",
        )


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


def test_validator_passes_when_surface_matches_current_all(tmp_path: Path) -> None:
    module = _load_validator()
    _write_public_modules(tmp_path, rates_exports=["SwapPricer"])
    module.write_current_surface(tmp_path)

    result = module.validate_public_api_surface(tmp_path)

    assert result.ok is True


def test_validator_rejects_added_public_export(tmp_path: Path) -> None:
    module = _load_validator()
    _write_public_modules(tmp_path, rates_exports=["SwapPricer"])
    module.write_current_surface(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "rates" / "__init__.py",
        "__all__ = ['ExperimentalSwapPricer', 'SwapPricer']\n",
    )

    result = module.validate_public_api_surface(tmp_path)

    assert result.ok is False
    assert result.errors == ["Added public export: fuggers_py.rates.ExperimentalSwapPricer"]


def test_validator_rejects_removed_public_export(tmp_path: Path) -> None:
    module = _load_validator()
    _write_public_modules(tmp_path, rates_exports=["SwapPricer", "SwapPricingResult"])
    module.write_current_surface(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "rates" / "__init__.py",
        "__all__ = ['SwapPricer']\n",
    )

    result = module.validate_public_api_surface(tmp_path)

    assert result.ok is False
    assert result.errors == ["Removed public export: fuggers_py.rates.SwapPricingResult"]


def test_update_writes_sorted_surface_json(tmp_path: Path) -> None:
    module = _load_validator()
    _write_public_modules(tmp_path, rates_exports=["SwapPricingResult", "SwapPricer"])

    module.write_current_surface(tmp_path)

    payload = json.loads((tmp_path / "specs" / "public_api_surface.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["modules"]["fuggers_py.rates"]["exports"] == ["SwapPricer", "SwapPricingResult"]


def test_update_refuses_tracked_surface_change_without_prompt_intent(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_public_modules(tmp_path, rates_exports=["SwapPricer"])
    module.write_current_surface(tmp_path)
    _git_commit_all(tmp_path, "baseline")
    _write_text(
        tmp_path / "src" / "fuggers_py" / "rates" / "__init__.py",
        "__all__ = ['ExperimentalSwapPricer', 'SwapPricer']\n",
    )

    try:
        module.update_public_api_surface(tmp_path)
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("update_public_api_surface should require prompt intent")

    assert message == (
        "Updating specs/public_api_surface.json requires an explicit user prompt such as "
        "`update public API surface` or `accept public API change`."
    )


def test_update_uses_prompt_intent_and_stop_permission_accepts_matching_contract(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_public_modules(tmp_path, rates_exports=["SwapPricer"])
    module.write_current_surface(tmp_path)
    _git_commit_all(tmp_path, "baseline")
    _write_text(
        tmp_path / "src" / "fuggers_py" / "rates" / "__init__.py",
        "__all__ = ['ExperimentalSwapPricer', 'SwapPricer']\n",
    )

    module.write_public_api_surface_intent(tmp_path, prompt="Please update public API surface for this export.")
    module.update_public_api_surface(tmp_path)

    result = module.validate_public_api_surface_contract_permission(tmp_path)

    assert result.ok is True


def test_stop_permission_rejects_manual_surface_contract_edit(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_public_modules(tmp_path, rates_exports=["SwapPricer"])
    module.write_current_surface(tmp_path)
    _git_commit_all(tmp_path, "baseline")
    payload = json.loads((tmp_path / "specs" / "public_api_surface.json").read_text(encoding="utf-8"))
    payload["modules"]["fuggers_py.rates"]["exports"].append("ExperimentalSwapPricer")
    (tmp_path / "specs" / "public_api_surface.json").write_text(json.dumps(payload), encoding="utf-8")

    result = module.validate_public_api_surface_contract_permission(tmp_path)

    assert result.ok is False
    assert result.reason == (
        "specs/public_api_surface.json changed without an allowed public API surface update. "
        "Ask explicitly to update the public API surface, then run `python tools/update_public_api_surface.py`."
    )


def test_contract_permission_base_ref_accepts_generated_surface_change(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_public_modules(tmp_path, rates_exports=["SwapPricer"])
    module.write_current_surface(tmp_path)
    _git_commit_all(tmp_path, "baseline")
    base_ref = _git_head(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / "rates" / "__init__.py",
        "__all__ = ['ExperimentalSwapPricer', 'SwapPricer']\n",
    )
    module.write_current_surface(tmp_path)
    _git_commit_all(tmp_path, "generated surface contract update")

    result = module.validate_public_api_surface_contract_permission(tmp_path, base_ref=base_ref)

    assert result.ok is True


def test_contract_permission_base_ref_rejects_stale_surface_change(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_public_modules(tmp_path, rates_exports=["SwapPricer"])
    module.write_current_surface(tmp_path)
    _git_commit_all(tmp_path, "baseline")
    base_ref = _git_head(tmp_path)

    payload = json.loads((tmp_path / "specs" / "public_api_surface.json").read_text(encoding="utf-8"))
    payload["modules"]["fuggers_py.rates"]["exports"].append("ExperimentalSwapPricer")
    (tmp_path / "specs" / "public_api_surface.json").write_text(json.dumps(payload), encoding="utf-8")
    _git_commit_all(tmp_path, "manual surface contract edit")

    result = module.validate_public_api_surface_contract_permission(tmp_path, base_ref=base_ref)

    assert result.ok is False
    assert result.reason == (
        "specs/public_api_surface.json changed, but it does not match the current public `__all__` exports."
    )
