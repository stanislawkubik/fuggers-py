"""Bond relative-value analytics."""

from __future__ import annotations

from .asw_basis_cds_links import AswBasisCdsLinkBreakdown, decompose_asw_basis_cds_links
from .basis_swapped_bonds import (
    CommonCurrencyFixedBondView,
    CommonCurrencyFloatingBondView,
    bond_to_common_currency_fixed,
    bond_to_common_currency_floating,
)
from .bond_switch import BondSwitchTrade
from .butterfly import ButterflyTrade, construct_butterfly
from .global_bond_rv import GlobalUsdSofrRvResult, global_usd_sofr_rv
from .neutrality import NeutralityTarget, NeutralizedTradeExpression, TradeLeg, neutralize_choices
from .rich_cheap import RichCheapSignal, rank_rich_cheap
from .selection import (
    BondChoice,
    BondSignal,
    MaturityChoice,
    MaturitySignal,
    SignalDirection,
    select_bond_choice,
    select_maturity_choice,
)
from .usd_sofr_yardstick import UsdSofrAdjustedRvMeasure, usd_sofr_adjusted_rv_from_links
from .workflow import RvWorkflowResult, bond_signal_workflow, maturity_signal_workflow

__all__ = [
    "AswBasisCdsLinkBreakdown",
    "BondChoice",
    "BondSignal",
    "BondSwitchTrade",
    "ButterflyTrade",
    "CommonCurrencyFixedBondView",
    "CommonCurrencyFloatingBondView",
    "GlobalUsdSofrRvResult",
    "MaturityChoice",
    "MaturitySignal",
    "NeutralityTarget",
    "NeutralizedTradeExpression",
    "RichCheapSignal",
    "RvWorkflowResult",
    "SignalDirection",
    "TradeLeg",
    "UsdSofrAdjustedRvMeasure",
    "bond_to_common_currency_fixed",
    "bond_to_common_currency_floating",
    "bond_signal_workflow",
    "construct_butterfly",
    "decompose_asw_basis_cds_links",
    "global_usd_sofr_rv",
    "maturity_signal_workflow",
    "neutralize_choices",
    "rank_rich_cheap",
    "select_bond_choice",
    "select_maturity_choice",
    "usd_sofr_adjusted_rv_from_links",
]
