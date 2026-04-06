"""UK gilt conventions."""

from __future__ import annotations

from ..types import YieldCalculationRules


def uk_gilt_rules() -> YieldCalculationRules:
    """Return the bundled UK gilt yield-calculation rules."""

    return YieldCalculationRules.uk_gilt()


__all__ = ["uk_gilt_rules"]
