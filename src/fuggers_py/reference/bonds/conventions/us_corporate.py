"""US corporate bond conventions."""

from __future__ import annotations

from ..types import YieldCalculationRules


def us_corporate_rules() -> YieldCalculationRules:
    """Return the bundled US corporate bond yield-calculation rules."""

    return YieldCalculationRules.us_corporate()


__all__ = ["us_corporate_rules"]
