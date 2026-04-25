"""US Treasury conventions."""

from __future__ import annotations

from fuggers_py._core import YieldCalculationRules


def us_treasury_rules() -> YieldCalculationRules:
    """Return the bundled US Treasury yield-calculation rules."""

    return YieldCalculationRules.us_treasury()


__all__ = ["us_treasury_rules"]
