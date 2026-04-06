from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.market.curves import DiscountCurveBuilder
from fuggers_py.calc import CurveBuilder
from fuggers_py.core import CurveId

from tests.helpers._engine_scenarios import SETTLEMENT, scenario_a_curve_points


def test_engine_curve_builder_named_curve_creation_and_update() -> None:
    builder = CurveBuilder()
    curve = builder.add_zero_curve(CurveId("usd.discount"), list(reversed(scenario_a_curve_points())), SETTLEMENT)
    fetched = builder.get("usd.discount")

    assert fetched is curve
    assert list(builder.inputs_for("usd.discount").tenors()) == [
        Decimal("0.25"),
        Decimal("0.50"),
        Decimal("1.00"),
        Decimal("2.00"),
        Decimal("5.00"),
        Decimal("10.00"),
    ]

    direct = DiscountCurveBuilder(reference_date=SETTLEMENT)
    for point in scenario_a_curve_points():
        direct.add_zero_rate(float(point.tenor), point.value)
    direct_curve = direct.build()

    assert curve.zero_rate_at_tenor(3.0) == pytest.approx(direct_curve.zero_rate_at_tenor(3.0), rel=1e-12)
    assert curve.discount_factor(SETTLEMENT.add_years(1)) > curve.discount_factor(SETTLEMENT.add_years(5)) > curve.discount_factor(SETTLEMENT.add_years(10))

    updated_points = scenario_a_curve_points()
    updated_points[-1] = type(updated_points[-1])(Decimal("10.00"), Decimal("0.0410"))
    builder.add_zero_curve("usd.discount", updated_points, SETTLEMENT)
    assert builder.get("usd.discount").zero_rate_at_tenor(10.0) == pytest.approx(0.0410, rel=1e-12)
