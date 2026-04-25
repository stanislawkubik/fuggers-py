from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Date
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.curves.kernels.nodes import LinearZeroKernel


def _sloped_zero_curve(*, day_count: str = "ACT/360") -> YieldCurve:
    return YieldCurve(
        spec=CurveSpec(
            name="tests.sloped-zero",
            reference_date=Date.from_ymd(2026, 4, 17),
            day_count=day_count,
            currency="USD",
            type="nominal",
            extrapolation_policy="error",
        ),
        kernel=LinearZeroKernel(
            tenors=(1.0, 2.0, 3.0),
            zero_rates=(0.01, 0.02, 0.03),
        ),
    )


def _zero_rate_delta(base_curve: YieldCurve, bumped_curve, tenor: float) -> Decimal:
    return Decimal(str(bumped_curve.zero_rate_at(tenor))) - Decimal(str(base_curve.rate_at(tenor)))


def test_shifted_curve_uses_requested_tenor_on_non_act_365_curve() -> None:
    curve = _sloped_zero_curve(day_count="ACT/360")
    bumped = curve.shifted(shift=0.0001)

    assert bumped.rate_at(2.0) == pytest.approx(0.0201)


def test_shifted_curve_changes_zero_rate_by_exact_bump_size() -> None:
    curve = _sloped_zero_curve()
    bumped = curve.shifted(shift=0.0001)

    assert _zero_rate_delta(curve, bumped, 2.0) == pytest.approx(Decimal("0.0001"))


def test_bumped_curve_changes_requested_tenor_zero_rate_by_exact_bump_size() -> None:
    curve = _sloped_zero_curve()
    bumped = curve.bumped(
        tenor_grid=(1.0, 2.0, 3.0),
        bumps={2.0: 0.0001},
    )

    assert _zero_rate_delta(curve, bumped, 2.0) == pytest.approx(Decimal("0.0001"))


def test_bumped_curve_uses_default_key_rate_grid_when_grid_is_omitted() -> None:
    curve = _sloped_zero_curve()
    bumped = curve.bumped(bumps={2.0: 0.0001})

    assert _zero_rate_delta(curve, bumped, 2.0) == pytest.approx(Decimal("0.0001"))


def test_bumped_curve_can_move_multiple_tenors() -> None:
    curve = _sloped_zero_curve()
    bumped = curve.bumped(
        tenor_grid=(1.0, 2.0, 3.0),
        bumps={1.0: 0.0001, 3.0: -0.0002},
    )

    assert _zero_rate_delta(curve, bumped, 1.0) == pytest.approx(Decimal("0.0001"))
    assert _zero_rate_delta(curve, bumped, 2.0) == pytest.approx(Decimal("0"))
    assert _zero_rate_delta(curve, bumped, 3.0) == pytest.approx(Decimal("-0.0002"))
