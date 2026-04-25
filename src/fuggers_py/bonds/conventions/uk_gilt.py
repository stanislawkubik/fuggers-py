"""UK gilt conventions."""

from __future__ import annotations

from fuggers_py._core import YieldCalculationRules


def uk_gilt_rules() -> YieldCalculationRules:
    """Return the bundled UK gilt yield-calculation rules."""

    return YieldCalculationRules.uk_gilt()


__all__ = ["uk_gilt_rules"]
