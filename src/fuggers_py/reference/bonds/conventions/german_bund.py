"""German Bund conventions."""

from __future__ import annotations

from ..types import YieldCalculationRules


def german_bund_rules() -> YieldCalculationRules:
    """Return the bundled German Bund yield-calculation rules."""

    return YieldCalculationRules.german_bund()


__all__ = ["german_bund_rules"]
