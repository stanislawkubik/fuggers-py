"""Rates product definitions for swaps, FRAs, futures, inflation swaps, and options.

The rates package groups the tradable contract objects used across vanilla and
exotic rates workflows, including leg specifications, swap structures, option
wrappers, and deliverable futures helpers.
"""

from __future__ import annotations

from fuggers_py.products.instruments import HasExpiry, HasOptionType, HasUnderlyingInstrument

from . import futures, options
from .asset_swap import AssetSwap
from .basis_swap import BasisSwap, SameCurrencyBasisSwap
from .common import AccrualPeriod, FixedLegSpec, FloatingLegSpec, PayReceive, ScheduleDefinition
from .cross_currency_basis import CrossCurrencyBasisSwap
from .fixed_float_swap import FixedFloatSwap, InterestRateSwap
from .fra import ForwardRateAgreement, Fra
from .futures import DeliverableBasket, DeliverableBond, GovernmentBondFuture
from .ois import Ois, OvernightIndexedSwap
from .options import CapFloor, CapFloorType, FuturesOption, OptionType, Swaption
from .standard_coupon_inflation_swap import StandardCouponInflationSwap
from .zero_coupon_inflation_swap import ZeroCouponInflationSwap

__all__ = [
    "AccrualPeriod",
    "AssetSwap",
    "BasisSwap",
    "CapFloor",
    "CapFloorType",
    "CrossCurrencyBasisSwap",
    "DeliverableBasket",
    "DeliverableBond",
    "FixedFloatSwap",
    "FixedLegSpec",
    "FloatingLegSpec",
    "ForwardRateAgreement",
    "Fra",
    "futures",
    "FuturesOption",
    "GovernmentBondFuture",
    "HasExpiry",
    "HasOptionType",
    "HasUnderlyingInstrument",
    "InterestRateSwap",
    "Ois",
    "OptionType",
    "options",
    "OvernightIndexedSwap",
    "PayReceive",
    "SameCurrencyBasisSwap",
    "ScheduleDefinition",
    "StandardCouponInflationSwap",
    "Swaption",
    "ZeroCouponInflationSwap",
]
