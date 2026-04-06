from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

from tests.helpers._paths import REPO_ROOT

ROOT = REPO_ROOT
_FINAL_RELEASE_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=None if env is None else {**os.environ, **env},
    )


def _dist_version(path: Path) -> str:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as wheel:
            metadata_name = next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
            metadata_text = wheel.read(metadata_name).decode()
    elif path.suffixes[-2:] == [".tar", ".gz"]:
        with tarfile.open(path, "r:gz") as sdist:
            metadata_member = next(member for member in sdist.getmembers() if member.name.endswith("PKG-INFO"))
            metadata_text = sdist.extractfile(metadata_member).read().decode()
    else:
        raise AssertionError(f"Unsupported distribution type: {path}")

    for line in metadata_text.splitlines():
        if line.startswith("Version: "):
            return line.split(": ", 1)[1]
    raise AssertionError(f"Could not find Version metadata in {path}")


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _install_and_read_version(artifact: Path, tmp_path: Path) -> dict[str, str]:
    venv_dir = tmp_path / f"venv-{artifact.stem.replace('.', '-')}"
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    python = _venv_python(venv_dir)
    _run(
        str(python),
        "-m",
        "pip",
        "install",
        str(artifact),
        cwd=ROOT,
        env={"PIP_DISABLE_PIP_VERSION_CHECK": "1"},
    )
    completed = _run(
        str(python),
        "-c",
        (
            "import json, importlib.metadata, fuggers_py; "
            "print(json.dumps({"
            "\"runtime\": fuggers_py.__version__, "
            "\"metadata\": importlib.metadata.version('fuggers-py')"
            "}))"
        ),
        cwd=ROOT,
    )
    return json.loads(completed.stdout.strip())


def _current_environment_versions() -> dict[str, str]:
    completed = _run(
        sys.executable,
        "-c",
        (
            "import json, importlib.metadata, pathlib, fuggers_py; "
            "source_root = (pathlib.Path.cwd() / 'src').resolve(); "
            "versions = ["
            "(pathlib.Path(dist.locate_file('')).resolve(), dist.version) "
            "for dist in importlib.metadata.distributions() "
            "if dist.metadata.get('Name') == 'fuggers-py'"
            "]; "
            "metadata_version = next("
            "(version for location, version in versions if location == source_root), "
            "importlib.metadata.version('fuggers-py')"
            "); "
            "print(json.dumps({"
            "\"runtime\": fuggers_py.__version__, "
            "\"metadata\": metadata_version"
            "}))"
        ),
        cwd=ROOT,
    )
    return json.loads(completed.stdout.strip())


@pytest.fixture(scope="module")
def built_distributions(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path | str]:
    if not (ROOT / ".git").exists():
        pytest.skip("Packaging consistency tests require a git checkout with .git metadata present.")

    tmp_root = tmp_path_factory.mktemp("packaging-consistency")
    build_out = tmp_root / "build-out"
    pip_out = tmp_root / "pip-wheel-out"
    build_out.mkdir()
    pip_out.mkdir()

    common_env = {"PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    _run(sys.executable, "-m", "build", "--outdir", str(build_out), cwd=ROOT, env=common_env)
    _run(sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(pip_out), cwd=ROOT, env=common_env)

    build_wheel = next(build_out.glob("*.whl"))
    build_sdist = next(build_out.glob("*.tar.gz"))
    pip_wheel = next(pip_out.glob("*.whl"))
    build_version = _dist_version(build_wheel)
    pip_version = _dist_version(pip_wheel)
    sdist_version = _dist_version(build_sdist)

    return {
        "build_wheel": build_wheel,
        "build_sdist": build_sdist,
        "pip_wheel": pip_wheel,
        "build_version": build_version,
        "pip_version": pip_version,
        "sdist_version": sdist_version,
    }


def test_supported_local_build_paths_produce_consistent_versions(
    built_distributions: dict[str, Path | str],
) -> None:
    build_version = built_distributions["build_version"]
    pip_version = built_distributions["pip_version"]
    sdist_version = built_distributions["sdist_version"]

    assert build_version
    assert pip_version
    assert sdist_version
    assert build_version == pip_version == sdist_version
    assert not build_version.startswith("0.0.0")


def test_installed_wheel_and_sdist_metadata_match_runtime_version(
    built_distributions: dict[str, Path | str],
    tmp_path: Path,
) -> None:
    expected_version = built_distributions["build_version"]
    wheel_result = _install_and_read_version(built_distributions["build_wheel"], tmp_path)
    sdist_result = _install_and_read_version(built_distributions["build_sdist"], tmp_path)

    assert wheel_result["runtime"] == expected_version
    assert wheel_result["metadata"] == expected_version
    assert sdist_result["runtime"] == expected_version
    assert sdist_result["metadata"] == expected_version


def test_current_environment_metadata_matches_built_distribution_version(
    built_distributions: dict[str, Path | str],
) -> None:
    expected_version = built_distributions["build_version"]
    current = _current_environment_versions()

    assert current["runtime"] == expected_version
    assert current["metadata"] == expected_version


def test_expected_release_version_is_exact_if_requested(
    built_distributions: dict[str, Path | str],
) -> None:
    expected_version = os.environ.get("EXPECTED_RELEASE_VERSION")
    if expected_version is None:
        pytest.skip("EXPECTED_RELEASE_VERSION is not set.")

    build_version = built_distributions["build_version"]
    pip_version = built_distributions["pip_version"]
    sdist_version = built_distributions["sdist_version"]
    current = _current_environment_versions()

    assert _FINAL_RELEASE_RE.fullmatch(expected_version), expected_version
    assert build_version == expected_version
    assert pip_version == expected_version
    assert sdist_version == expected_version
    assert current["runtime"] == expected_version
    assert current["metadata"] == expected_version


def test_expected_release_version_has_no_prerelease_or_local_suffix_if_requested(
    built_distributions: dict[str, Path | str],
) -> None:
    expected_version = os.environ.get("EXPECTED_RELEASE_VERSION")
    if expected_version is None:
        pytest.skip("EXPECTED_RELEASE_VERSION is not set.")

    assert ".dev" not in expected_version
    assert "+" not in expected_version
    assert "a" not in expected_version
    assert "b" not in expected_version
    assert "rc" not in expected_version
