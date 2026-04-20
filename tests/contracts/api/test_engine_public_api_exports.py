from __future__ import annotations

import importlib

import pytest

from fuggers_py.portfolio import Portfolio, Position


@pytest.mark.parametrize(
    "module_name",
    (
        "fuggers_py.calc",
        "fuggers_py.calc.scheduler",
        "fuggers_py.market",
        "fuggers_py.market.snapshot",
        "fuggers_py.market.state",
        "fuggers_py.market.sources",
        "fuggers_py.reference",
    ),
)
def test_engine_transition_namespaces_are_no_longer_public(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


def test_portfolio_root_remains_part_of_the_final_public_surface(fixed_rate_2025_bond) -> None:
    position = Position(fixed_rate_2025_bond, quantity=2, label="bond")
    portfolio = Portfolio.new([position], currency=fixed_rate_2025_bond.currency())

    assert portfolio.total_quantity() == 2
