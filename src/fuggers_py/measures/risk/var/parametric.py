"""Parametric VaR (`fuggers_py.measures.risk.var.parametric`).

Parametric VaR returns a non-negative loss magnitude in raw decimal units.
The DV01-based helper treats the supplied shock as a basis-point magnitude and
returns a positive-magnitude loss estimate.
"""

from __future__ import annotations

from decimal import Decimal
from statistics import NormalDist, mean, stdev

from fuggers_py.measures.errors import AnalyticsError

from .types import VaRResult, VaRMethod


def _validate_confidence(confidence: float) -> float:
    level = float(confidence)
    if not 0.0 < level < 1.0:
        raise AnalyticsError.invalid_input("confidence must lie strictly between 0 and 1.")
    return level


def parametric_var(returns: list[float], confidence: float = 0.95) -> VaRResult:
    """Compute parametric VaR from a sample of returns.

    Returns
    -------
    VaRResult
        Non-negative loss magnitude at the requested confidence level.
    """

    level = _validate_confidence(confidence)
    if not returns:
        return VaRResult(value=Decimal(0), confidence=Decimal(str(level)), method=VaRMethod.PARAMETRIC)
    mu = mean(float(r) for r in returns)
    sigma = stdev(float(r) for r in returns) if len(returns) > 1 else 0.0
    left_tail_quantile = NormalDist().inv_cdf(1.0 - level)
    var_value = max(0.0, -(mu + sigma * left_tail_quantile))
    return VaRResult(
        value=Decimal(str(var_value)),
        confidence=Decimal(str(level)),
        method=VaRMethod.PARAMETRIC,
    )


def parametric_var_from_dv01(dv01: object, shock_bps: float, confidence: float = 0.95) -> VaRResult:
    """Compute a DV01-based VaR estimate from a basis-point shock magnitude.

    The shock is interpreted as an absolute move in basis points.
    """

    level = _validate_confidence(confidence)
    z = NormalDist().inv_cdf(level)
    value = abs(Decimal(str(dv01))) * abs(Decimal(str(shock_bps))) * Decimal(str(z))
    return VaRResult(
        value=value,
        confidence=Decimal(str(level)),
        method=VaRMethod.PARAMETRIC,
    )


__all__ = ["parametric_var", "parametric_var_from_dv01"]
