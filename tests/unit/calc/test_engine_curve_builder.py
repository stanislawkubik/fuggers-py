from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.calc import CurveBuilder
from fuggers_py.calc.errors import CurveNotFoundError
from fuggers_py.core import CurveId, Date
from fuggers_py.market.curves import CurveType
from fuggers_py.market.snapshot import CurveInputs, CurvePoint
from tests.helpers._public_curve_helpers import linear_zero_curve


SETTLEMENT = Date.from_ymd(2026, 1, 15)


def _scenario_points() -> list[CurvePoint]:
    return [
        CurvePoint(Decimal("0.25"), Decimal("0.0450")),
        CurvePoint(Decimal("0.50"), Decimal("0.0445")),
        CurvePoint(Decimal("1.00"), Decimal("0.0435")),
        CurvePoint(Decimal("2.00"), Decimal("0.0415")),
        CurvePoint(Decimal("5.00"), Decimal("0.0395")),
        CurvePoint(Decimal("10.00"), Decimal("0.0400")),
    ]


def test_engine_curve_builder_stores_finished_curves_and_raw_inputs() -> None:
    builder = CurveBuilder()
    points = list(reversed(_scenario_points()))
    curve_inputs = CurveInputs.from_points(CurveId("usd.discount"), SETTLEMENT, points)
    curve = linear_zero_curve("usd.discount", SETTLEMENT, points, curve_type=CurveType.OVERNIGHT_DISCOUNT)

    builder.add_from_inputs(curve_inputs)
    builder.add_curve("usd.discount", curve)

    fetched = builder.get("usd.discount")
    built_curve = builder.built_curve("usd.discount")

    assert fetched is curve
    assert list(builder.inputs_for("usd.discount").tenors()) == [
        Decimal("0.25"),
        Decimal("0.50"),
        Decimal("1.00"),
        Decimal("2.00"),
        Decimal("5.00"),
        Decimal("10.00"),
    ]
    assert built_curve.unwrap() is curve
    assert built_curve.date() == SETTLEMENT


def test_engine_curve_builder_updates_stored_curve_without_rebuilding() -> None:
    builder = CurveBuilder()
    initial_points = _scenario_points()
    updated_points = _scenario_points()
    updated_points[-1] = type(updated_points[-1])(Decimal("10.00"), Decimal("0.0410"))

    builder.add_curve(
        "usd.discount",
        linear_zero_curve("usd.discount", SETTLEMENT, initial_points, curve_type=CurveType.OVERNIGHT_DISCOUNT),
        curve_inputs=CurveInputs.from_points("usd.discount", SETTLEMENT, initial_points),
    )
    builder.add_curve(
        "usd.discount",
        linear_zero_curve("usd.discount", SETTLEMENT, updated_points, curve_type=CurveType.OVERNIGHT_DISCOUNT),
        curve_inputs=CurveInputs.from_points("usd.discount", SETTLEMENT, updated_points),
    )

    assert builder.get("usd.discount").zero_rate_at(10.0) == pytest.approx(0.0410, rel=1e-12)
    assert builder.inputs_for("usd.discount").points[-1].value == Decimal("0.0410")


def test_engine_curve_builder_requires_finished_curve_objects() -> None:
    builder = CurveBuilder()

    with pytest.raises(ValueError, match="built curve object"):
        builder.add_curve("usd.discount", None)

    with pytest.raises(CurveNotFoundError):
        builder.get("usd.discount")
