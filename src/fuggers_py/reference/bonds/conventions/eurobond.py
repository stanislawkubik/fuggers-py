"""Eurobond conventions."""

from __future__ import annotations

from ..types import YieldCalculationRules


def eurobond_rules() -> YieldCalculationRules:
    """Return the bundled Eurobond yield-calculation rules."""

    return YieldCalculationRules.eurobond()


__all__ = ["eurobond_rules"]
