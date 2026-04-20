"""Rates option pricers and closed-form models.

This namespace exposes the Black-76, Bachelier, and Hull-White proxy pricing
engines together with their shared result types.
"""

from __future__ import annotations

from ._common import CapFloorPricingResult, CapFloorletPricingResult, FuturesOptionPricingResult, OptionFormulaResult, OptionGreeks, SwaptionPricingResult
from .bachelier import BachelierPricer, bachelier_formula
from .black76 import Black76Pricer, black76_formula
from .hull_white import HullWhiteOptionPricer, HullWhiteRateOptionModel, hull_white_normal_volatility

__all__ = [
    "BachelierPricer",
    "Black76Pricer",
    "CapFloorPricingResult",
    "CapFloorletPricingResult",
    "FuturesOptionPricingResult",
    "HullWhiteOptionPricer",
    "HullWhiteRateOptionModel",
    "OptionFormulaResult",
    "OptionGreeks",
    "SwaptionPricingResult",
    "bachelier_formula",
    "black76_formula",
    "hull_white_normal_volatility",
]
