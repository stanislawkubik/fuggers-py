from __future__ import annotations

import pytest

from fuggers_py.core.types import Date
from fuggers_py.market.curves.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py.market.curves.errors import TenorOutOfBounds
from fuggers_py.market.curves.value_type import ValueType


def test_try_value_at_bounds_checking() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = DiscreteCurve(
        ref,
        tenors=[1.0, 2.0],
        values=[0.95, 0.90],
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )

    with pytest.raises(TenorOutOfBounds):
        _ = curve.try_value_at(0.5)
    assert curve.try_value_at(1.5) == pytest.approx(curve.value_at(1.5))


def test_date_to_tenor_and_tenor_to_date_round_trip() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = DiscreteCurve(
        ref,
        tenors=[1.0, 2.0],
        values=[0.95, 0.90],
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )

    d = ref.add_days(400)
    t = curve.date_to_tenor(d)
    d2 = curve.tenor_to_date(t)
    assert abs(d.days_between(d2)) <= 1

    assert curve.date_to_tenor(ref.add_days(365)) == pytest.approx(1.0)
    assert curve.tenor_to_date(1.0) == ref.add_days(365)
