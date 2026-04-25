from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "src/fuggers_py/_core/ids.py",
    "src/fuggers_py/_math/numerical.py",
    "src/fuggers_py/bonds/cashflows/irregular.py",
    "src/fuggers_py/bonds/_yields/solver.py",
    "src/fuggers_py/bonds/_yields/street.py",
    "src/fuggers_py/credit/analytics.py",
    "src/fuggers_py/credit/pricing.py",
    "src/fuggers_py/credit/risk.py",
    "src/fuggers_py/curves/conversion.py",
    "src/fuggers_py/curves/date_support.py",
    "src/fuggers_py/curves/spec.py",
    "src/fuggers_py/funding/analytics.py",
    "src/fuggers_py/funding/products.py",
    "src/fuggers_py/inflation/analytics.py",
    "src/fuggers_py/inflation/conventions.py",
    "src/fuggers_py/inflation/pricing.py",
    "src/fuggers_py/rates/futures/reference.py",
    "typecheck/public_api.py",
]
RUFF_RULES = "E4,E7,E9,F,I,UP"


def main() -> int:
    cmd = ["ruff", "check", "--select", RUFF_RULES, *TARGETS]
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
