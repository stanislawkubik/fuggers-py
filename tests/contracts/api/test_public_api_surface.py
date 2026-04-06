from __future__ import annotations

import importlib
from importlib import metadata
from pathlib import Path

import pytest

import fuggers_py
from fuggers_py.calc import PricingRouter as calc_pricing_router
from fuggers_py.core import Date as core_date
from fuggers_py.core import InstrumentId as core_instrument_id
from fuggers_py.core import Price as core_price
from fuggers_py.market.curves import RateCurve as market_rate_curve
from fuggers_py.measures.functions import (
    yield_to_maturity as measures_yield_to_maturity,
)
from fuggers_py.portfolio import Portfolio as portfolio_portfolio
from fuggers_py.products.bonds import FixedBondBuilder as products_fixed_bond_builder
from tests.helpers._paths import REPO_ROOT

ROOT = REPO_ROOT
REMOVED_ROOTS = (
    "analytics",
    "bonds",
    "credit",
    "curves",
    "data",
    "engine",
    "funding",
    "inflation",
    "io",
    "rates",
)


def _local_metadata_version() -> str:
    source_root = (ROOT / "src").resolve()
    for dist in metadata.distributions():
        if dist.metadata.get("Name") != "fuggers-py":
            continue
        if Path(dist.locate_file("")).resolve() == source_root:
            return dist.version
    from fuggers_py._version import version

    return version


def test_explicit_submodule_imports_match_expected_public_symbols() -> None:
    from fuggers_py.calc import PricingRouter
    from fuggers_py.core import Date, InstrumentId, Price
    from fuggers_py.market.curves import RateCurve
    from fuggers_py.measures.functions import yield_to_maturity
    from fuggers_py.portfolio import Portfolio
    from fuggers_py.products.bonds import FixedBondBuilder

    assert Date is core_date
    assert InstrumentId is core_instrument_id
    assert Price is core_price
    assert RateCurve is market_rate_curve
    assert FixedBondBuilder is products_fixed_bond_builder
    assert yield_to_maturity is measures_yield_to_maturity
    assert Portfolio is portfolio_portfolio
    assert PricingRouter is calc_pricing_router


def test_top_level_package_exports_match_current_surface() -> None:
    assert set(fuggers_py.__all__) == {
        "__version__",
        "adapters",
        "calc",
        "core",
        "market",
        "math",
        "measures",
        "portfolio",
        "pricers",
        "products",
        "reference",
    }


def test_top_level_package_version_is_available_and_matches_distribution_metadata() -> None:
    assert fuggers_py.__version__
    assert any(char.isdigit() for char in fuggers_py.__version__)
    assert _local_metadata_version() == fuggers_py.__version__


@pytest.mark.parametrize("root_name", REMOVED_ROOTS)
def test_removed_roots_are_not_importable(root_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(f"fuggers_py.{root_name}")
