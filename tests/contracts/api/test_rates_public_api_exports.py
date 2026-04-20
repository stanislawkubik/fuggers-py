from __future__ import annotations

import ast
from pathlib import Path

import fuggers_py.rates as rates_pkg

from fuggers_py.rates import (
    AccrualPeriod,
    AssetSwapBreakdown,
    CrossCurrencyBasisSwap,
    CrossCurrencyBasisSwapPricer,
    CrossCurrencyBasisSwapPricingResult,
    FixedLegSpec,
    IndexFixingStore,
    IndexSource,
    LookbackDays,
    OvernightIndexedSwap,
    PublicationTime,
    SameCurrencyBasisSwap,
    ScheduleDefinition,
    ShiftType,
    SwapQuote,
    SwapPricingResult,
    BondIndex,
    IndexConventions,
    OvernightCompounding,
)


def test_rates_root_is_a_small_direct_import_surface() -> None:
    rates_init = Path(rates_pkg.__file__)
    tree = ast.parse(rates_init.read_text(encoding="utf-8"))

    assert "__getattr__" not in {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "__getattr__" not in {node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in {"import_module", "__import__"}
            elif isinstance(node.func, ast.Attribute):
                assert not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "importlib"
                    and node.func.attr == "import_module"
                )


def test_rates_root_exports_the_full_nominal_rates_surface() -> None:
    expected_key_exports = {
        "AccrualPeriod",
        "AssetSwap",
        "AssetSwapPricer",
        "BasisSwap",
        "BasisSwapQuote",
        "BondFutureQuote",
        "CrossCurrencyBasisSwap",
        "CrossCurrencyBasisSwapPricer",
        "FixedFloatSwap",
        "Fra",
        "FraPricer",
        "FuturesOption",
        "GovernmentBondFuture",
        "IndexFixingStore",
        "IndexSource",
        "OvernightCompounding",
        "PublicationTime",
        "SameCurrencyBasisSwap",
        "SwapPricer",
        "SwapQuote",
        "Swaption",
        "cheapest_to_deliver",
        "swap_dv01",
    }

    assert expected_key_exports <= set(rates_pkg.__all__)
    assert "InflationSwapPricer" not in rates_pkg.__all__
    assert "StandardCouponInflationSwap" not in rates_pkg.__all__
    assert "ZeroCouponInflationSwap" not in rates_pkg.__all__


def test_rates_root_exposes_products_quotes_pricing_and_fixing_helpers() -> None:
    assert rates_pkg.AccrualPeriod is AccrualPeriod
    assert rates_pkg.AssetSwapBreakdown is AssetSwapBreakdown
    assert rates_pkg.CrossCurrencyBasisSwap is CrossCurrencyBasisSwap
    assert rates_pkg.CrossCurrencyBasisSwapPricer is CrossCurrencyBasisSwapPricer
    assert rates_pkg.CrossCurrencyBasisSwapPricingResult is CrossCurrencyBasisSwapPricingResult
    assert rates_pkg.FixedLegSpec is FixedLegSpec
    assert rates_pkg.IndexFixingStore is IndexFixingStore
    assert rates_pkg.IndexSource is IndexSource
    assert rates_pkg.LookbackDays is LookbackDays
    assert rates_pkg.OvernightIndexedSwap is OvernightIndexedSwap
    assert rates_pkg.PublicationTime is PublicationTime
    assert rates_pkg.SameCurrencyBasisSwap is SameCurrencyBasisSwap
    assert rates_pkg.ScheduleDefinition is ScheduleDefinition
    assert rates_pkg.ShiftType is ShiftType
    assert rates_pkg.SwapPricingResult is SwapPricingResult
    assert SwapQuote.__module__ == "fuggers_py.rates.quotes"


def test_rates_fixing_symbols_are_owned_by_public_rates_module() -> None:
    assert BondIndex.__module__ == "fuggers_py.rates.indices"
    assert IndexConventions.__module__ == "fuggers_py.rates.indices"
    assert IndexFixingStore.__module__ == "fuggers_py.rates.indices"
    assert OvernightCompounding.__module__ == "fuggers_py.rates.indices"
