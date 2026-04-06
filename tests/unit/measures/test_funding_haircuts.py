from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.funding import (
    all_in_financing_cost,
    financed_cash,
    haircut_amount,
    haircut_drag,
    haircut_financing_cost,
)


def test_haircut_financing_helpers_compute_amounts_costs_and_drag() -> None:
    collateral_value = Decimal("1000000")
    haircut = Decimal("0.02")
    year_fraction = Decimal("0.25")

    assert haircut_amount(collateral_value=collateral_value, haircut=haircut) == Decimal("20000.00")
    assert financed_cash(collateral_value=collateral_value, haircut=haircut) == Decimal("980000.00")
    assert haircut_financing_cost(
        collateral_value=collateral_value,
        haircut=haircut,
        funding_rate=Decimal("0.06"),
        year_fraction=year_fraction,
    ) == Decimal("300.00000")
    assert all_in_financing_cost(
        collateral_value=collateral_value,
        haircut=haircut,
        repo_rate=Decimal("0.04"),
        haircut_funding_rate=Decimal("0.06"),
        year_fraction=year_fraction,
    ) == Decimal("10100.00000")
    assert haircut_drag(
        collateral_value=collateral_value,
        haircut=haircut,
        repo_rate=Decimal("0.04"),
        haircut_funding_rate=Decimal("0.06"),
        year_fraction=year_fraction,
    ) == Decimal("100.00000")
