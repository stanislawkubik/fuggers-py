"""Option analytics helpers for the analytics layer.

This package re-exports the pricing-model Greeks container and the relative
value helpers used by option analytics. Greeks are expressed in the native
units returned by the pricing model, so the public helpers here preserve the
raw sensitivities unless a scaling helper says otherwise. Relative-value
signals report the implied-minus-realized volatility gap and a vega notional
scaled by the requested volatility-point size.
"""

from __future__ import annotations

from fuggers_py.pricers.bonds.options import BinomialTree, HullWhiteModel, ModelError, ShortRateModel
from fuggers_py.pricers.rates.options import HullWhiteOptionPricer, HullWhiteRateOptionModel, OptionGreeks

HullWhite = HullWhiteModel

from .greeks import add_option_greeks, aggregate_option_greeks, extract_option_greeks, scale_option_greeks
from .rv import OptionRvSignal, implied_minus_realized_volatility, option_rv_signal, vega_notional

__all__ = [
    "BinomialTree",
    "HullWhite",
    "HullWhiteModel",
    "HullWhiteOptionPricer",
    "HullWhiteRateOptionModel",
    "ModelError",
    "OptionGreeks",
    "OptionRvSignal",
    "ShortRateModel",
    "add_option_greeks",
    "aggregate_option_greeks",
    "extract_option_greeks",
    "implied_minus_realized_volatility",
    "option_rv_signal",
    "scale_option_greeks",
    "vega_notional",
]
