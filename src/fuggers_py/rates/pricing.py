"""Rates-domain pricing exports for the first-layer public facade."""

from __future__ import annotations

from fuggers_py._pricers.rates import futures, options, risk
from fuggers_py._pricers.rates.asset_swap import AssetSwapBreakdown, AssetSwapPricer, AssetSwapPricingResult
from fuggers_py._pricers.rates.basis_swap_pricer import BasisSwapPricer, BasisSwapPricingResult
from fuggers_py._pricers.rates.cross_currency_basis import CrossCurrencyBasisSwapPricer, CrossCurrencyBasisSwapPricingResult
from fuggers_py._pricers.rates.fra_pricer import FraPricer, FraPricingResult
from fuggers_py._pricers.rates.swap_pricer import SwapPricer, SwapPricingResult

__all__ = [
    "AssetSwapBreakdown",
    "AssetSwapPricer",
    "AssetSwapPricingResult",
    "BasisSwapPricer",
    "BasisSwapPricingResult",
    "CrossCurrencyBasisSwapPricer",
    "CrossCurrencyBasisSwapPricingResult",
    "FraPricer",
    "FraPricingResult",
    "SwapPricer",
    "SwapPricingResult",
    "futures",
    "options",
    "risk",
]
