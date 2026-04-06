from __future__ import annotations

import subprocess
import sys
from importlib import metadata

import pytest

from tests.helpers._paths import REPO_ROOT

ROOT = REPO_ROOT


def test_release_ruff_gate_matches_pinned_dev_toolchain() -> None:
    version = metadata.version("ruff")
    if not version.startswith("0.15."):
        pytest.skip(f"release Ruff gate requires the pinned dev Ruff line; found {version}")
    completed = subprocess.run(
        [sys.executable, "tools/run_release_ruff.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, (
        f"Installed Ruff version: {version}\n"
        f"python tools/run_release_ruff.py failed with exit code {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
