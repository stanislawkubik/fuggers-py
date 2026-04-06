"""Historical VaR (`fuggers_py.measures.risk.var.historical`).

Historical VaR returns a non-negative loss magnitude in raw decimal units.
"""

from __future__ import annotations

from decimal import Decimal
from math import ceil, floor

from fuggers_py.measures.errors import AnalyticsError

from .types import VaRResult, VaRMethod


def _validate_confidence(confidence: float) -> float:
    level = float(confidence)
    if not 0.0 < level < 1.0:
        raise AnalyticsError.invalid_input("confidence must lie strictly between 0 and 1.")
    return level


def _left_tail_quantile(sorted_returns: list[float], probability: float) -> float:
    if len(sorted_returns) == 1:
        return sorted_returns[0]
    position = probability * (len(sorted_returns) - 1)
    lower = floor(position)
    upper = ceil(position)
    if lower == upper:
        return sorted_returns[lower]
    weight = position - lower
    return sorted_returns[lower] + weight * (sorted_returns[upper] - sorted_returns[lower])


def historical_var(returns: list[float], confidence: float = 0.95) -> VaRResult:
    """Compute historical VaR from a list of returns.

    Parameters
    ----------
    returns:
        Sample of period returns in raw decimal form.
    confidence:
        Confidence level between 0 and 1.

    Returns
    -------
    VaRResult
        Non-negative loss magnitude at the requested confidence level.
    """

    level = _validate_confidence(confidence)
    if not returns:
        return VaRResult(value=Decimal(0), confidence=Decimal(str(level)), method=VaRMethod.HISTORICAL)
    sorted_returns = sorted(float(r) for r in returns)
    tail_prob = 1.0 - level
    var_value = max(0.0, -_left_tail_quantile(sorted_returns, tail_prob))
    return VaRResult(
        value=Decimal(str(var_value)),
        confidence=Decimal(str(level)),
        method=VaRMethod.HISTORICAL,
    )


__all__ = ["historical_var"]
