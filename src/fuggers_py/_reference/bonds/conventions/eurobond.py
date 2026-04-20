"""Eurobond conventions."""

from __future__ import annotations

from fuggers_py._core import YieldCalculationRules


def eurobond_rules() -> YieldCalculationRules:
    """Return the bundled Eurobond yield-calculation rules."""

    return YieldCalculationRules.eurobond()


__all__ = ["eurobond_rules"]
