from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import fuggers_py.inflation as inflation_pkg
import fuggers_py.rates as rates_pkg
from fuggers_py.inflation import (
    InflationConvention,
    InflationError,
    InflationProjection,
    InflationSwapPricer,
    LinkerSwapParityCheck,
    StandardCouponInflationSwap,
    StandardCouponInflationSwapPeriodPricing,
    StandardCouponInflationSwapPricingResult,
    ZeroCouponInflationSwap,
    ZeroCouponInflationSwapPricingResult,
    breakeven_inflation_rate,
    linker_swap_parity_check,
    USD_CPI_U_NSA,
    reference_cpi,
    reference_index_ratio,
)


def test_inflation_root_is_a_small_direct_import_surface() -> None:
    inflation_init = Path(inflation_pkg.__file__)
    tree = ast.parse(inflation_init.read_text(encoding="utf-8"))

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


def test_inflation_root_exports_the_full_inflation_surface() -> None:
    expected_key_exports = {
        "InflationConvention",
        "InflationError",
        "InflationProjection",
        "InflationSwapPricer",
        "LinkerSwapParityCheck",
        "StandardCouponInflationSwap",
        "StandardCouponInflationSwapPeriodPricing",
        "StandardCouponInflationSwapPricingResult",
        "USD_CPI_U_NSA",
        "ZeroCouponInflationSwap",
        "ZeroCouponInflationSwapPricingResult",
        "breakeven_inflation_rate",
        "load_monthly_cpi_fixings_csv",
        "nominal_real_yield_basis",
        "reference_cpi",
        "reference_index_ratio",
    }

    assert expected_key_exports <= set(inflation_pkg.__all__)
    assert inflation_pkg.InflationError is InflationError
    assert inflation_pkg.InflationProjection is InflationProjection
    assert inflation_pkg.InflationSwapPricer is InflationSwapPricer
    assert inflation_pkg.StandardCouponInflationSwap is StandardCouponInflationSwap
    assert inflation_pkg.StandardCouponInflationSwapPeriodPricing is StandardCouponInflationSwapPeriodPricing
    assert inflation_pkg.StandardCouponInflationSwapPricingResult is StandardCouponInflationSwapPricingResult
    assert inflation_pkg.ZeroCouponInflationSwap is ZeroCouponInflationSwap
    assert inflation_pkg.ZeroCouponInflationSwapPricingResult is ZeroCouponInflationSwapPricingResult
    assert "InflationSwapPricer" not in rates_pkg.__all__


def test_inflation_root_helpers_are_usable_from_first_layer_imports() -> None:
    breakeven = breakeven_inflation_rate(
        nominal_yield=Decimal("0.05"),
        real_yield=Decimal("0.02"),
    )
    parity = linker_swap_parity_check(
        nominal_yield=Decimal("0.05"),
        real_yield=Decimal("0.02"),
        inflation_swap_rate=Decimal("0.029"),
    )

    assert callable(reference_cpi)
    assert callable(reference_index_ratio)
    assert breakeven == Decimal("1.05") / Decimal("1.02") - Decimal("1")
    assert isinstance(parity, LinkerSwapParityCheck)
    assert parity.linker_breakeven == breakeven


def test_inflation_symbols_are_owned_by_public_inflation_modules() -> None:
    assert InflationConvention.__module__ == "fuggers_py.inflation.reference"
    assert USD_CPI_U_NSA.__class__.__module__ == "fuggers_py.inflation.reference"
    assert reference_cpi.__module__ == "fuggers_py.inflation.reference"
    assert reference_index_ratio.__module__ == "fuggers_py.inflation.reference"
    assert ZeroCouponInflationSwap.__module__ == "fuggers_py.inflation"
    assert StandardCouponInflationSwap.__module__ == "fuggers_py.inflation"
    assert InflationSwapPricer.__module__ == "fuggers_py.inflation"
