"""Rates option products, pricing engines, and result records."""

from __future__ import annotations

from ..instruments import HasExpiry, HasOptionType, HasUnderlyingInstrument
from ._pricing_common import (
    CapFloorPricingResult,
    CapFloorletPricingResult,
    FuturesOptionPricingResult,
    OptionFormulaResult,
    OptionGreeks,
    SwaptionPricingResult,
)
from .bachelier import BachelierPricer, bachelier_formula
from .black76 import Black76Pricer, black76_formula
from .cap_floor import CapFloor, CapFloorType
from .futures_option import FuturesOption
from .greeks import add_option_greeks, aggregate_option_greeks, extract_option_greeks, scale_option_greeks
from .hull_white import HullWhiteOptionPricer, HullWhiteRateOptionModel, hull_white_normal_volatility
from .rv import OptionRvSignal, implied_minus_realized_volatility, option_rv_signal, vega_notional
from .swaption import Swaption

__all__ = [
    "BachelierPricer",
    "Black76Pricer",
    "CapFloor",
    "CapFloorPricingResult",
    "CapFloorType",
    "CapFloorletPricingResult",
    "FuturesOption",
    "FuturesOptionPricingResult",
    "HasExpiry",
    "HasOptionType",
    "HasUnderlyingInstrument",
    "HullWhiteOptionPricer",
    "HullWhiteRateOptionModel",
    "OptionFormulaResult",
    "OptionGreeks",
    "OptionRvSignal",
    "Swaption",
    "SwaptionPricingResult",
    "add_option_greeks",
    "aggregate_option_greeks",
    "bachelier_formula",
    "black76_formula",
    "extract_option_greeks",
    "hull_white_normal_volatility",
    "implied_minus_realized_volatility",
    "option_rv_signal",
    "scale_option_greeks",
    "vega_notional",
]
