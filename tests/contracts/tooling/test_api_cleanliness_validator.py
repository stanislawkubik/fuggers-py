from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def _load_validator() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "validate_api_cleanliness.py"
    spec = importlib.util.spec_from_file_location("validate_api_cleanliness_module", module_path)
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


def test_validator_rejects_revived_old_public_namespace(tmp_path: Path) -> None:
    module = _load_validator()
    path = "src/fuggers_py/products/bonds.py"
    _write_text(tmp_path / path, "__all__ = []\n")

    result = module.validate_api_cleanliness(tmp_path, paths={path})

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/products/bonds.py revives old public namespace `fuggers_py.products`. "
        "Use the current first-layer public modules instead."
    )


def test_validator_rejects_legacy_private_import_from_public_module(tmp_path: Path) -> None:
    module = _load_validator()
    path = "src/fuggers_py/rates/pricing.py"
    _write_text(
        tmp_path / path,
        "\n".join(
            [
                "from __future__ import annotations",
                "from fuggers_py._pricers.rates.swap_pricer import SwapPricer",
                "__all__ = ['SwapPricer']",
                "",
            ]
        ),
    )

    result = module.validate_api_cleanliness(tmp_path, paths={path})

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/rates/pricing.py:2 imports legacy API path "
        "`fuggers_py._pricers.rates.swap_pricer`. Use the current first-layer public module or move the implementation."
    )


def test_validator_rejects_sys_modules_alias_in_public_module(tmp_path: Path) -> None:
    module = _load_validator()
    path = "src/fuggers_py/rates/__init__.py"
    _write_text(
        tmp_path / path,
        "\n".join(
            [
                "import sys",
                "from fuggers_py.rates.pricing import SwapPricer",
                "sys.modules['fuggers_py.pricers.rates'] = sys.modules[__name__]",
                "__all__ = ['SwapPricer']",
                "",
            ]
        ),
    )

    result = module.validate_api_cleanliness(tmp_path, paths={path})

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/rates/__init__.py:3 touches `sys.modules`. "
        "Do not keep old import paths alive with module aliases."
    )


def test_validator_allows_explicit_first_layer_facade(tmp_path: Path) -> None:
    module = _load_validator()
    path = "src/fuggers_py/rates/pricing.py"
    _write_text(
        tmp_path / path,
        "\n".join(
            [
                "from __future__ import annotations",
                "from .swap_pricer import SwapPricer, SwapPricingResult",
                "__all__ = ['SwapPricer', 'SwapPricingResult']",
                "",
            ]
        ),
    )

    result = module.validate_api_cleanliness(tmp_path, paths={path})

    assert result.ok is True


def test_base_ref_checks_committed_pr_diff(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "src" / "fuggers_py" / "rates" / "__init__.py", "__all__ = []\n")
    _git_commit_all(tmp_path, "baseline")
    base_ref = _git_head(tmp_path)

    path = "src/fuggers_py/products/bonds.py"
    _write_text(tmp_path / path, "__all__ = []\n")
    _git_commit_all(tmp_path, "revive old namespace")

    result = module.validate_api_cleanliness(tmp_path, base_ref=base_ref)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/products/bonds.py revives old public namespace `fuggers_py.products`. "
        "Use the current first-layer public modules instead."
    )
