from __future__ import annotations

from decimal import Decimal

from fuggers_py.bonds.rv import rank_rich_cheap

from tests.helpers._fitted_bond_helpers import exponential_model, fit_result


def test_rich_cheap_ranking_orders_bonds_by_bp_residual() -> None:
    result = fit_result(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
        mispricings={
            "UST4Y": Decimal("0.90"),
            "UST8Y": Decimal("-1.40"),
            "UST10Y": Decimal("-0.20"),
        },
    )
    ranking = rank_rich_cheap(result, threshold_bps=Decimal("1"))

    assert ranking[0].instrument_id.as_str() == "UST8Y"
    assert ranking[0].classification == "CHEAP"
    assert ranking[-1].instrument_id.as_str() == "UST4Y"
    assert ranking[-1].classification == "RICH"
