from __future__ import annotations

import ast
import inspect
from pathlib import Path

import fuggers_py.funding as funding_pkg
from fuggers_py.funding import (
    HaircutQuote,
    RepoQuote,
    RepoTrade,
    all_in_financing_cost,
    financed_cash,
    futures_invoice_amount,
    haircut_amount,
    haircut_drag,
    haircut_financing_cost,
    implied_repo_rate,
    implied_repo_rate_from_trade,
    is_special,
    repo_carry_return,
    repo_financing_cost,
    repo_net_carry,
    specialness_spread,
    specialness_value,
)


def test_funding_root_is_a_small_direct_import_surface() -> None:
    funding_init = Path(funding_pkg.__file__)
    tree = ast.parse(funding_init.read_text(encoding="utf-8"))

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


def test_funding_root_exports_current_first_layer_surface() -> None:
    expected_key_exports = {
        "HaircutQuote",
        "RepoQuote",
        "RepoTrade",
        "all_in_financing_cost",
        "futures_invoice_amount",
        "haircut_financing_cost",
        "implied_repo_rate",
        "repo_carry_return",
        "repo_net_carry",
        "specialness_value",
    }

    assert expected_key_exports <= set(funding_pkg.__all__)
    assert funding_pkg.HaircutQuote is HaircutQuote
    assert funding_pkg.RepoQuote is RepoQuote
    assert funding_pkg.RepoTrade is RepoTrade
    assert funding_pkg.all_in_financing_cost is all_in_financing_cost
    assert funding_pkg.financed_cash is financed_cash
    assert funding_pkg.futures_invoice_amount is futures_invoice_amount
    assert funding_pkg.haircut_amount is haircut_amount
    assert funding_pkg.haircut_drag is haircut_drag
    assert funding_pkg.haircut_financing_cost is haircut_financing_cost
    assert funding_pkg.implied_repo_rate is implied_repo_rate
    assert funding_pkg.implied_repo_rate_from_trade is implied_repo_rate_from_trade
    assert funding_pkg.is_special is is_special
    assert funding_pkg.repo_carry_return is repo_carry_return
    assert funding_pkg.repo_financing_cost is repo_financing_cost
    assert funding_pkg.repo_net_carry is repo_net_carry
    assert funding_pkg.specialness_spread is specialness_spread
    assert funding_pkg.specialness_value is specialness_value
    assert RepoTrade.__module__ == "fuggers_py.funding.products"
    assert repo_carry_return.__module__ == "fuggers_py.funding.analytics"
    assert repo_financing_cost.__module__ == "fuggers_py.funding.analytics"
    assert repo_net_carry.__module__ == "fuggers_py.funding.analytics"
    assert futures_invoice_amount.__module__ == "fuggers_py.funding.analytics"
    assert implied_repo_rate.__module__ == "fuggers_py.funding.analytics"
    assert implied_repo_rate_from_trade.__module__ == "fuggers_py.funding.analytics"
    assert RepoQuote.__module__ == "fuggers_py.funding.quotes"
    assert HaircutQuote.__module__ == "fuggers_py.funding.quotes"


def test_funding_exports_resolve_under_funding() -> None:
    root = Path(funding_pkg.__file__).resolve().parent
    for name in funding_pkg.__all__:
        value = getattr(funding_pkg, name)
        try:
            source = inspect.getsourcefile(value)
        except TypeError:
            source = inspect.getsourcefile(type(value))
        assert source is not None
        assert Path(source).resolve().is_relative_to(root), name
