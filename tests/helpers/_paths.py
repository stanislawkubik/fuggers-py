from __future__ import annotations

from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
DATA_ROOT = TESTS_ROOT / "fixtures" / "data"
FIXTURES_ROOT = TESTS_ROOT / "fixtures"
