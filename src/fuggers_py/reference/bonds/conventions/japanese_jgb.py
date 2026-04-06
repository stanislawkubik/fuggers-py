"""Japanese JGB conventions."""

from __future__ import annotations

from ..types import YieldCalculationRules


def japanese_jgb_rules() -> YieldCalculationRules:
    """Return the bundled Japanese government bond yield rules."""

    return YieldCalculationRules.japanese_jgb()


__all__ = ["japanese_jgb_rules"]
