from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from fuggers_py.bonds import BondQuote
from fuggers_py.credit import CdsQuote
from fuggers_py.funding import HaircutQuote, RepoQuote
from fuggers_py.rates import BasisSwapQuote, BondFutureQuote, FxForwardQuote, SwapQuote


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
    return imported_modules


def test_market_namespace_is_no_longer_public() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py.market")


def test_domain_owned_quotes_are_the_only_public_quote_homes() -> None:
    assert BondQuote.__module__ == "fuggers_py.bonds.quotes"
    assert RepoQuote.__module__ == "fuggers_py.funding.quotes"
    assert SwapQuote.__module__ == "fuggers_py.rates.quotes"
    assert BasisSwapQuote.__module__ == "fuggers_py.rates.quotes"
    assert BondFutureQuote.__module__ == "fuggers_py.rates.quotes"
    assert FxForwardQuote.__module__ == "fuggers_py.rates.quotes"
    assert CdsQuote.__module__ == "fuggers_py.credit.quotes"
    assert HaircutQuote.__module__ == "fuggers_py.funding.quotes"


def test_public_quote_modules_do_not_import_market_bucket_helpers() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    quote_module_paths = (
        repo_root / "src" / "fuggers_py" / "bonds" / "quotes.py",
        repo_root / "src" / "fuggers_py" / "rates" / "quotes.py",
        repo_root / "src" / "fuggers_py" / "credit" / "quotes.py",
        repo_root / "src" / "fuggers_py" / "funding" / "quotes.py",
    )

    for path in quote_module_paths:
        imported_modules = _imported_modules(path)
        assert not any(module_name.startswith("fuggers_py._market") for module_name in imported_modules), path
