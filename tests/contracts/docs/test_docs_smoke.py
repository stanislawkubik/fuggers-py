from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers._paths import REPO_ROOT

ROOT = REPO_ROOT
DOC_SMOKE_CASES: dict[str, tuple[int, ...]] = {
    "README.md": (0,),
    "docs/SRC_STRUCTURE.md": (0,),
    "docs/api/bonds.md": (0,),
    "docs/api/rates.md": (0,),
    "docs/api/inflation.md": (0,),
    "docs/api/credit.md": (0,),
    "docs/api/funding.md": (0,),
}


def _python_blocks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return re.findall(r"```python\n(.*?)\n```", text, flags=re.DOTALL)


@pytest.mark.parametrize("relative_path, block_indexes", DOC_SMOKE_CASES.items())
def test_selected_markdown_python_blocks_smoke(relative_path: str, block_indexes: tuple[int, ...]) -> None:
    path = ROOT / relative_path
    blocks = _python_blocks(path)
    script = "\n\n".join(blocks[index] for index in block_indexes)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, (
        f"{relative_path} failed with exit code {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


@pytest.mark.parametrize("relative_path", ["README.md", "docs/SRC_STRUCTURE.md"])
def test_public_docs_do_not_depend_on_repo_fixture_paths(relative_path: str) -> None:
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    assert "tests/data" not in text
