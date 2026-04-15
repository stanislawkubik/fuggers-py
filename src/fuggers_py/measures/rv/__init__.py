"""Relative-value analytics for fitted-bond and cross-asset workflows.

The package mixes two RV styles today:

- cross-asset spread-view helpers built on the live rates pricers
- older fitted-bond workflows that still depend on the legacy fitted-bond model

Imports are lazy so the working slice can be used without importing every older
RV module up front.
"""

from __future__ import annotations

from importlib import import_module


_VALUE_EXPORTS = {
    "AswBasisCdsLinkBreakdown": "fuggers_py.measures.rv.asw_basis_cds_links",
    "decompose_asw_basis_cds_links": "fuggers_py.measures.rv.asw_basis_cds_links",
    "CommonCurrencyFixedBondView": "fuggers_py.measures.rv.basis_swapped_bonds",
    "CommonCurrencyFloatingBondView": "fuggers_py.measures.rv.basis_swapped_bonds",
    "bond_to_common_currency_fixed": "fuggers_py.measures.rv.basis_swapped_bonds",
    "bond_to_common_currency_floating": "fuggers_py.measures.rv.basis_swapped_bonds",
    "BondSwitchTrade": "fuggers_py.measures.rv.bond_switch",
    "ButterflyTrade": "fuggers_py.measures.rv.butterfly",
    "construct_butterfly": "fuggers_py.measures.rv.butterfly",
    "GlobalUsdSofrRvResult": "fuggers_py.measures.rv.global_bond_rv",
    "global_usd_sofr_rv": "fuggers_py.measures.rv.global_bond_rv",
    "NeutralityTarget": "fuggers_py.measures.rv.neutrality",
    "NeutralizedTradeExpression": "fuggers_py.measures.rv.neutrality",
    "TradeLeg": "fuggers_py.measures.rv.neutrality",
    "neutralize_choices": "fuggers_py.measures.rv.neutrality",
    "RichCheapSignal": "fuggers_py.measures.rv.rich_cheap",
    "rank_rich_cheap": "fuggers_py.measures.rv.rich_cheap",
    "BondChoice": "fuggers_py.measures.rv.selection",
    "BondSignal": "fuggers_py.measures.rv.selection",
    "MaturityChoice": "fuggers_py.measures.rv.selection",
    "MaturitySignal": "fuggers_py.measures.rv.selection",
    "SignalDirection": "fuggers_py.measures.rv.selection",
    "select_bond_choice": "fuggers_py.measures.rv.selection",
    "select_maturity_choice": "fuggers_py.measures.rv.selection",
    "UsdSofrAdjustedRvMeasure": "fuggers_py.measures.rv.usd_sofr_yardstick",
    "usd_sofr_adjusted_rv_from_links": "fuggers_py.measures.rv.usd_sofr_yardstick",
    "RvWorkflowResult": "fuggers_py.measures.rv.workflow",
    "bond_signal_workflow": "fuggers_py.measures.rv.workflow",
    "maturity_signal_workflow": "fuggers_py.measures.rv.workflow",
}

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


def __getattr__(name: str) -> object:
    module_name = _VALUE_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
