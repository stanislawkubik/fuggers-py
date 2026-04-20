"""Rates-domain product exports for the first-layer public facade."""

from __future__ import annotations

from fuggers_py._core import OptionType, PayReceive
from fuggers_py._products.instruments import HasExpiry, HasOptionType, HasUnderlyingInstrument
from fuggers_py._products.rates import futures, options
from fuggers_py._products.rates.asset_swap import AssetSwap
from fuggers_py._products.rates.basis_swap import BasisSwap, SameCurrencyBasisSwap
from fuggers_py._products.rates.common import AccrualPeriod, FixedLegSpec, FloatingLegSpec, ScheduleDefinition
from fuggers_py._products.rates.cross_currency_basis import CrossCurrencyBasisSwap
from fuggers_py._products.rates.fixed_float_swap import FixedFloatSwap, InterestRateSwap
from fuggers_py._products.rates.fra import ForwardRateAgreement, Fra
from fuggers_py._products.rates.futures import DeliverableBasket, DeliverableBond, GovernmentBondFuture
from fuggers_py._products.rates.ois import Ois, OvernightIndexedSwap
from fuggers_py._products.rates.options import CapFloor, CapFloorType, FuturesOption, Swaption

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
    "OptionType",
    "OvernightIndexedSwap",
    "PayReceive",
    "SameCurrencyBasisSwap",
    "ScheduleDefinition",
    "Swaption",
    "futures",
    "options",
]
