"""Hedge ratio helpers (`fuggers_py.measures.risk.hedging.hedge_ratio`).

Ratios are expressed as face notionals or scaling factors needed to offset the
target risk measure.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class HedgeDirection(str, Enum):
    """Direction of the hedge leg relative to the target position."""

    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class HedgeRecommendation:
    """Suggested hedge ratio and direction.

    Parameters
    ----------
    ratio:
        Hedge size as a positive scaling factor.
    direction:
        Long or short hedge leg direction.
    reason:
        Optional human-readable explanation.
    """

    ratio: Decimal
    direction: HedgeDirection
    reason: str | None = None


def duration_hedge_ratio(
    target_duration: object,
    target_price: object,
    hedge_duration: object,
    hedge_price: object,
    *,
    target_face: object = Decimal(100),
    hedge_face: object = Decimal(100),
) -> Decimal:
    """Return the hedge ratio implied by duration and market value.

    The calculation uses positive market values and face amounts, so the
    result is a magnitude rather than a signed exposure.

    Returns
    -------
    Decimal
        Ratio of target face notional to hedge face notional.
    """

    td = _to_decimal(target_duration)
    tp = _to_decimal(target_price)
    hd = _to_decimal(hedge_duration)
    hp = _to_decimal(hedge_price)
    tf = _to_decimal(target_face)
    hf = _to_decimal(hedge_face)
    if tp <= 0 or hp <= 0:
        raise ValueError("target_price and hedge_price must be positive.")
    if tf == 0 or hf == 0:
        raise ValueError("target_face and hedge_face must be non-zero.")
    hedge_dollar_duration = hd * hp * hf
    if hedge_dollar_duration == 0:
        return Decimal(0)
    target_dollar_duration = td * tp * tf
    return target_dollar_duration / hedge_dollar_duration


def dv01_hedge_ratio(
    target_dv01: object,
    hedge_dv01: object,
) -> Decimal:
    """Return the hedge ratio implied by target and hedge DV01 magnitudes.

    Returns
    -------
    Decimal
        Target DV01 divided by hedge DV01, or zero when hedge DV01 is zero.
    """

    td = _to_decimal(target_dv01)
    hd = _to_decimal(hedge_dv01)
    if hd == 0:
        return Decimal(0)
    return td / hd


__all__ = [
    "HedgeDirection",
    "HedgeRecommendation",
    "duration_hedge_ratio",
    "dv01_hedge_ratio",
]
