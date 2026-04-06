from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.rv import construct_bond_switch

from tests.helpers._fitted_bond_helpers import exponential_model, fit_result


def test_bond_switch_selects_the_cheapest_and_richest_bonds_and_sizes_a_duration_hedge() -> None:
    result = fit_result(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
        mispricings={
            "UST4Y": Decimal("0.90"),
            "UST8Y": Decimal("-1.40"),
        },
    )
    switch = construct_bond_switch(result)

    assert switch.cheap_instrument_id.as_str() == "UST8Y"
    assert switch.rich_instrument_id.as_str() == "UST4Y"
    assert switch.sell_notional > Decimal(0)
    assert switch.duration_hedge_ratio > Decimal(0)
    assert switch.expected_bp_convergence > Decimal(0)
    assert switch.expected_price_convergence > Decimal(0)
