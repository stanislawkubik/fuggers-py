"""Basic relative-value helpers for options.

The volatility gap is returned as a raw decimal. Vega notional is computed by
multiplying model vega by a volatility-point size, with the default ``0.01``
representing a 1 vol-point move.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ._pricing_common import OptionGreeks

from .greeks import extract_option_greeks


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class OptionRvSignal:
    """Option RV snapshot with volatility gap and vega-notional scaling.

    Attributes
    ----------
    implied_volatility:
        Implied volatility in raw decimal form.
    realized_volatility:
        Realized volatility in raw decimal form.
    volatility_gap:
        Implied minus realized volatility.
    vega:
        Option vega in native model units.
    vega_notional:
        Vega scaled by the requested volatility-point size.
    """

    implied_volatility: Decimal
    realized_volatility: Decimal
    volatility_gap: Decimal
    vega: Decimal
    vega_notional: Decimal


def implied_minus_realized_volatility(implied_volatility: object, realized_volatility: object) -> Decimal:
    """Return implied minus realized volatility as a raw decimal.

    Positive values mean implied volatility exceeds realized volatility.
    """
    return _to_decimal(implied_volatility) - _to_decimal(realized_volatility)


def vega_notional(greeks: OptionGreeks | object, *, volatility_point: object = Decimal("0.01")) -> Decimal:
    """Return vega scaled by the supplied volatility-point size."""
    resolved_greeks = extract_option_greeks(greeks)
    return resolved_greeks.vega * _to_decimal(volatility_point)


def option_rv_signal(
    *,
    implied_volatility: object,
    realized_volatility: object,
    greeks: OptionGreeks | object,
    volatility_point: object = Decimal("0.01"),
) -> OptionRvSignal:
    """Build an option RV signal from implied and realized volatilities."""
    resolved_implied = _to_decimal(implied_volatility)
    resolved_realized = _to_decimal(realized_volatility)
    resolved_greeks = extract_option_greeks(greeks)
    gap = resolved_implied - resolved_realized
    return OptionRvSignal(
        implied_volatility=resolved_implied,
        realized_volatility=resolved_realized,
        volatility_gap=gap,
        vega=resolved_greeks.vega,
        vega_notional=vega_notional(resolved_greeks, volatility_point=volatility_point),
    )


__all__ = ["OptionRvSignal", "implied_minus_realized_volatility", "option_rv_signal", "vega_notional"]
