from __future__ import annotations

import tomllib

from tests.helpers._paths import REPO_ROOT

ROOT = REPO_ROOT
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_ROOT = ROOT / "src" / "fuggers_py"


def _configured_measured_packages() -> list[str]:
    with PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    return list(data["tool"]["fuggers_source_coverage"]["measured_packages"])


def _public_top_level_packages() -> list[str]:
    return sorted(
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir()
        and not path.name.startswith("_")
        and (path / "__init__.py").exists()
    )


def _configured_mypy_paths():
    with PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    return [ROOT / path for path in data["tool"]["mypy"]["files"]]


def test_source_coverage_config_tracks_all_public_top_level_packages() -> None:
    configured = sorted(_configured_measured_packages())
    discovered = _public_top_level_packages()
    missing = sorted(set(discovered) - set(configured))

    assert not missing, (
        "tool.fuggers_source_coverage.measured_packages is missing public package roots.\n"
        f"missing: {missing}\n"
        f"configured: {configured}\n"
        f"discovered: {discovered}"
    )


def test_mypy_config_files_all_exist() -> None:
    missing = [path for path in _configured_mypy_paths() if not path.exists()]

    assert not missing, (
        "tool.mypy.files contains missing paths.\n"
        f"missing: {[str(path.relative_to(ROOT)) for path in missing]}"
    )
