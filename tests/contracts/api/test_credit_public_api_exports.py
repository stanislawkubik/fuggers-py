from __future__ import annotations

import ast
import inspect
from pathlib import Path

import fuggers_py.credit as credit_pkg
from fuggers_py.credit import (
    AdjustedCdsBreakdown,
    BondCdsBasisBreakdown,
    Cds,
    CdsPremiumPeriod,
    CdsPricer,
    CdsPricingResult,
    CdsQuote,
    CreditDefaultSwap,
    ProtectionSide,
    RiskFreeProxyBreakdown,
    adjusted_cds_breakdown,
    adjusted_cds_spread,
    bond_cds_basis,
    bond_cds_basis_breakdown,
    cds_cs01,
    cds_adjusted_risk_free_rate,
    proxy_risk_free_breakdown,
    risky_pv01,
)


def test_credit_root_is_a_small_direct_import_surface() -> None:
    credit_init = Path(credit_pkg.__file__)
    tree = ast.parse(credit_init.read_text(encoding="utf-8"))

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


def test_credit_root_exports_current_first_layer_surface() -> None:
    expected_key_exports = {
        "AdjustedCdsBreakdown",
        "BondCdsBasisBreakdown",
        "Cds",
        "CdsPremiumPeriod",
        "CdsPricer",
        "CdsPricingResult",
        "CdsQuote",
        "CreditDefaultSwap",
        "ProtectionSide",
        "RiskFreeProxyBreakdown",
        "adjusted_cds_spread",
        "bond_cds_basis",
        "cds_cs01",
        "proxy_risk_free_breakdown",
        "risky_pv01",
    }

    assert expected_key_exports <= set(credit_pkg.__all__)
    assert credit_pkg.Cds is Cds
    assert credit_pkg.CdsPremiumPeriod is CdsPremiumPeriod
    assert credit_pkg.CdsPricer is CdsPricer
    assert credit_pkg.CdsPricingResult is CdsPricingResult
    assert credit_pkg.CdsQuote is CdsQuote
    assert credit_pkg.CreditDefaultSwap is CreditDefaultSwap
    assert credit_pkg.ProtectionSide is ProtectionSide
    assert credit_pkg.AdjustedCdsBreakdown is AdjustedCdsBreakdown
    assert credit_pkg.BondCdsBasisBreakdown is BondCdsBasisBreakdown
    assert credit_pkg.RiskFreeProxyBreakdown is RiskFreeProxyBreakdown
    assert credit_pkg.adjusted_cds_breakdown is adjusted_cds_breakdown
    assert credit_pkg.adjusted_cds_spread is adjusted_cds_spread
    assert credit_pkg.bond_cds_basis is bond_cds_basis
    assert credit_pkg.bond_cds_basis_breakdown is bond_cds_basis_breakdown
    assert credit_pkg.cds_adjusted_risk_free_rate is cds_adjusted_risk_free_rate
    assert credit_pkg.cds_cs01 is cds_cs01
    assert credit_pkg.proxy_risk_free_breakdown is proxy_risk_free_breakdown
    assert credit_pkg.risky_pv01 is risky_pv01
    assert Cds.__module__ == "fuggers_py.credit.instruments"
    assert CreditDefaultSwap.__module__ == "fuggers_py.credit.instruments"
    assert CdsPricer.__module__ == "fuggers_py.credit.pricing"
    assert CdsPricingResult.__module__ == "fuggers_py.credit.pricing"
    assert AdjustedCdsBreakdown.__module__ == "fuggers_py.credit.analytics"
    assert BondCdsBasisBreakdown.__module__ == "fuggers_py.credit.analytics"
    assert RiskFreeProxyBreakdown.__module__ == "fuggers_py.credit.analytics"
    assert CdsQuote.__module__ == "fuggers_py.credit.quotes"
    assert cds_cs01.__module__ == "fuggers_py.credit.risk"
    assert risky_pv01.__module__ == "fuggers_py.credit.risk"


def test_credit_exports_resolve_under_credit() -> None:
    root = Path(credit_pkg.__file__).resolve().parent
    for name in credit_pkg.__all__:
        value = getattr(credit_pkg, name)
        try:
            source = inspect.getsourcefile(value)
        except TypeError:
            source = inspect.getsourcefile(type(value))
        assert source is not None
        assert Path(source).resolve().is_relative_to(root), name
