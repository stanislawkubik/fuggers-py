from __future__ import annotations

import pytest

from fuggers_py._core.types import Date
from fuggers_py._curves_impl.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py._curves_impl.value_type import ValueType


def test_value_at_date_uses_date_to_tenor() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = DiscreteCurve(
        ref,
        tenors=[1.0, 2.0],
        values=[0.95, 0.90],
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )

    target_date = ref.add_days(int(round(1.5 * 365)))
    assert curve.value_at_date(target_date) == pytest.approx(curve.value_at_tenor(1.5), abs=1e-2)


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
