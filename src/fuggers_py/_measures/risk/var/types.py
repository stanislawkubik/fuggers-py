"""VaR result types (`fuggers_py._measures.risk.var.types`)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class VaRMethod(str, Enum):
    """Method used to compute value at risk."""

    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"


@dataclass(frozen=True, slots=True)
class VaRResult:
    """Value-at-risk output container.

    Parameters
    ----------
    value:
        Non-negative loss magnitude in raw decimal units.
    confidence:
        Confidence level used for the estimate.
    method:
        Method used to compute the estimate.
    """

    value: Decimal
    confidence: Decimal
    method: VaRMethod


__all__ = ["VaRMethod", "VaRResult"]
