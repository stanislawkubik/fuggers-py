from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "src/fuggers_py/core",
    "src/fuggers_py/market/curves/conversion.py",
    "src/fuggers_py/market/curves/value_type.py",
    "src/fuggers_py/market/curves/term_structure.py",
    "src/fuggers_py/market/curves/wrappers/credit_curve.py",
    "src/fuggers_py/market/curves/wrappers/rate_curve.py",
    "src/fuggers_py/measures/cashflows/irregular.py",
    "src/fuggers_py/measures/yields/street.py",
    "src/fuggers_py/measures/yields/solver.py",
    "src/fuggers_py/portfolio/risk/__init__.py",
    "typecheck/public_api.py",
]
RUFF_RULES = "E4,E7,E9,F,I,UP"


def main() -> int:
    cmd = ["ruff", "check", "--select", RUFF_RULES, *TARGETS]
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
