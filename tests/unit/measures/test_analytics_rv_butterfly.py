from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.rv import construct_butterfly

from tests.helpers._fitted_bond_helpers import exponential_model, fit_result


def test_butterfly_construction_generates_positive_wing_weights_and_negative_body_weight() -> None:
    result = fit_result(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
        mispricings={
            "UST4Y": Decimal("-0.10"),
            "UST6Y": Decimal("0.50"),
            "UST8Y": Decimal("-0.15"),
        },
    )
    butterfly = construct_butterfly(
        result,
        short_wing_instrument_id="UST4Y",
        body_instrument_id="UST6Y",
        long_wing_instrument_id="UST8Y",
    )

    assert butterfly.short_wing_weight > Decimal(0)
    assert butterfly.long_wing_weight > Decimal(0)
    assert butterfly.body_weight < Decimal(0)
    assert butterfly.signal_bps > Decimal(0)
