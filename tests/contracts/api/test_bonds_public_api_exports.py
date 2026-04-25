from __future__ import annotations

import ast
import inspect
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import fuggers_py.bonds as bonds_pkg

from fuggers_py.bonds import (
    BinomialTree,
    BondPricer,
    BondQuote,
    BondResult,
    BondRiskCalculator,
    BondCashFlow,
    BondType,
    CallableBondBuilder,
    DurationResult,
    FixedBond,
    FixedBondBuilder,
    YASCalculator,
    HullWhiteModel,
    IssuerType,
    TipsBond,
    current_yield,
    g_spread,
)
from fuggers_py import Compounding, Date, Frequency, Yield, YieldCalculationRules


def test_bonds_root_is_a_small_direct_import_surface() -> None:
    bonds_init = Path(bonds_pkg.__file__)
    tree = ast.parse(bonds_init.read_text(encoding="utf-8"))

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


def _annual_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL)


def _base_bond(*, years: int = 5, coupon: str = "0.05") -> FixedBond:
    issue = Date.from_ymd(2024, 2, 20)
    return (
        FixedBondBuilder.new()
        .with_issue_date(issue)
        .with_maturity_date(issue.add_years(years))
        .with_coupon_rate(Decimal(coupon))
        .with_frequency(Frequency.ANNUAL)
        .with_rules(_annual_rules())
        .build()
    )


def test_bonds_root_imports_expose_current_first_layer_aliases() -> None:
    from fuggers_py import BondType as root_bond_type, IssuerType as root_issuer_type

    expected_key_exports = {
        "Bond",
        "BondCashFlow",
        "BondOption",
        "BondPricer",
        "BondQuote",
        "BondRiskCalculator",
        "CallableBondBuilder",
        "FixedBondBuilder",
        "HullWhiteModel",
        "KeyRateDurations",
        "OASCalculator",
        "SecurityId",
        "TipsBond",
        "YASCalculator",
        "YasAnalysis",
        "current_yield",
        "g_spread",
        "z_spread",
    }

    assert expected_key_exports <= set(bonds_pkg.__all__)
    assert bonds_pkg.BinomialTree is BinomialTree
    assert bonds_pkg.BondPricer is BondPricer
    assert bonds_pkg.BondQuote is BondQuote
    assert bonds_pkg.BondResult is BondResult
    assert bonds_pkg.BondRiskCalculator is BondRiskCalculator
    assert bonds_pkg.BondCashFlow is BondCashFlow
    assert bonds_pkg.CallableBondBuilder is CallableBondBuilder
    assert bonds_pkg.DurationResult is DurationResult
    assert bonds_pkg.FixedBondBuilder is FixedBondBuilder
    assert bonds_pkg.HullWhiteModel is HullWhiteModel
    assert bonds_pkg.TipsBond is TipsBond
    assert bonds_pkg.YASCalculator is YASCalculator
    assert bonds_pkg.current_yield is current_yield
    assert bonds_pkg.g_spread is g_spread
    assert BondType is root_bond_type
    assert BondType is bonds_pkg.BondType
    assert IssuerType is root_issuer_type
    assert IssuerType is bonds_pkg.IssuerType
    assert BondType.__module__ == "fuggers_py.bonds.types.bond_type"
    assert IssuerType.__module__ == "fuggers_py.bonds.types.issuer_type"
    assert BondQuote.__module__ == "fuggers_py.bonds.quotes"


def test_bonds_exports_resolve_under_bonds() -> None:
    root = Path(bonds_pkg.__file__).resolve().parent
    source_less_constants = {"DEFAULT_BUMP_SIZE", "SMALL_BUMP_SIZE"}
    for name in bonds_pkg.__all__:
        value = getattr(bonds_pkg, name)
        try:
            source = inspect.getsourcefile(value)
        except TypeError:
            assert name in source_less_constants
            continue
        assert source is not None
        assert Path(source).resolve().is_relative_to(root), name


def test_fixed_bond_builder_and_pricer_are_usable_from_root_exports() -> None:
    bond = _base_bond()
    settlement = Date.from_ymd(2024, 8, 20)
    ytm = Yield.new(Decimal("0.04"), compounding=Compounding.ANNUAL)

    price_result = BondPricer().price_from_yield(bond, ytm, settlement)
    duration_result = bond.risk_metrics(ytm, settlement)

    assert isinstance(price_result, BondResult)
    assert price_result.dirty_price == price_result.dirty
    assert price_result.clean_price == price_result.clean
    assert price_result.accrued_interest == price_result.accrued
    assert isinstance(duration_result, DurationResult)
    assert duration_result.duration == duration_result.modified_duration
    assert duration_result.pv01 == duration_result.dv01


def test_callable_bond_builder_is_usable_from_root_exports() -> None:
    base = _base_bond(years=5)
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(
            call_date=Date.from_ymd(2027, 2, 20),
            call_price=Decimal("101"),
        )
        .build()
    )

    assert callable_bond.call_price_on(Date.from_ymd(2027, 2, 20)) == Decimal("101")
