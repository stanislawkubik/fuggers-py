"""Relative-value analytics for fitted-bond and cross-asset workflows.

The public surface in this package focuses on fitted-curve rich/cheap
signals, signal selection, neutrality construction, asset-swap basis views,
and global bond RV helpers that convert between floating, fixed, and USD SOFR
frames. Returned spreads are typically raw decimals, while ranked signals and
trade summaries explain the chosen direction and neutrality assumptions.
"""

from __future__ import annotations

from .asw_basis_cds_links import AswBasisCdsLinkBreakdown, decompose_asw_basis_cds_links, decompose_floating_view_links
from .basis_swapped_bonds import (
    CommonCurrencyFixedBondView,
    CommonCurrencyFloatingBondView,
    bond_to_common_currency_fixed,
    bond_to_common_currency_floating,
)
from .bond_switch import BondSwitchTrade, construct_bond_switch
from .butterfly import ButterflyTrade, construct_butterfly
from .constant_maturity import ConstantMaturityBenchmark, generate_constant_maturity_benchmark
from .global_bond_rv import (
    GlobalFixedCashflowRvResult,
    GlobalUsdSofrRvResult,
    global_fixed_cashflow_rv,
    global_usd_sofr_rv,
)
from .new_issue import NewIssueFairValue, NewIssueRequest, estimate_new_issue_fair_value
from .neutrality import NeutralityTarget, NeutralizedTradeExpression, TradeLeg, neutralize_bond_pair, neutralize_choices
from .rich_cheap import RichCheapSignal, rank_rich_cheap
from .selection import (
    BondChoice,
    BondSignal,
    MaturityChoice,
    MaturitySignal,
    SignalDirection,
    select_bond_choice,
    select_bond_choices,
    select_maturity_choice,
    select_maturity_choices,
)
from .usd_sofr_yardstick import (
    UsdSofrAdjustedRvMeasure,
    usd_sofr_adjusted_rv_from_links,
    usd_sofr_adjusted_rv_measure,
)
from .workflow import RvWorkflowResult, bond_pair_trade, bond_signal_workflow, maturity_pair_trade, maturity_signal_workflow

__all__ = [
    "AswBasisCdsLinkBreakdown",
    "BondChoice",
    "BondSignal",
    "BondSwitchTrade",
    "ButterflyTrade",
    "CommonCurrencyFixedBondView",
    "CommonCurrencyFloatingBondView",
    "ConstantMaturityBenchmark",
    "GlobalFixedCashflowRvResult",
    "GlobalUsdSofrRvResult",
    "MaturityChoice",
    "MaturitySignal",
    "NewIssueFairValue",
    "NewIssueRequest",
    "NeutralityTarget",
    "NeutralizedTradeExpression",
    "RichCheapSignal",
    "RvWorkflowResult",
    "SignalDirection",
    "TradeLeg",
    "UsdSofrAdjustedRvMeasure",
    "bond_to_common_currency_fixed",
    "bond_to_common_currency_floating",
    "bond_pair_trade",
    "bond_signal_workflow",
    "construct_bond_switch",
    "construct_butterfly",
    "decompose_asw_basis_cds_links",
    "decompose_floating_view_links",
    "estimate_new_issue_fair_value",
    "generate_constant_maturity_benchmark",
    "global_fixed_cashflow_rv",
    "global_usd_sofr_rv",
    "maturity_pair_trade",
    "maturity_signal_workflow",
    "neutralize_bond_pair",
    "neutralize_choices",
    "rank_rich_cheap",
    "select_bond_choice",
    "select_bond_choices",
    "select_maturity_choice",
    "select_maturity_choices",
    "usd_sofr_adjusted_rv_from_links",
    "usd_sofr_adjusted_rv_measure",
]
