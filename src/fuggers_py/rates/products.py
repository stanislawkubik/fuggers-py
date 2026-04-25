"""Rates-domain product exports for the first-layer public facade."""

from __future__ import annotations

from . import futures, options
from .asset_swap import AssetSwap
from .basis_swap import BasisSwap, SameCurrencyBasisSwap
from .common import AccrualPeriod, FixedLegSpec, FloatingLegSpec, ScheduleDefinition
from .cross_currency_basis import CrossCurrencyBasisSwap
from .fixed_float_swap import FixedFloatSwap, InterestRateSwap
from .fra import ForwardRateAgreement, Fra
from .futures import DeliverableBasket, DeliverableBond, GovernmentBondFuture
from .instruments import HasExpiry, HasOptionType, HasUnderlyingInstrument
from .ois import Ois, OvernightIndexedSwap
from .options import CapFloor, CapFloorType, FuturesOption, Swaption

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
    "FuturesOption",
    "GovernmentBondFuture",
    "HasExpiry",
    "HasOptionType",
    "HasUnderlyingInstrument",
    "InterestRateSwap",
    "Ois",
    "OvernightIndexedSwap",
    "SameCurrencyBasisSwap",
    "ScheduleDefinition",
    "Swaption",
    "futures",
    "options",
]
