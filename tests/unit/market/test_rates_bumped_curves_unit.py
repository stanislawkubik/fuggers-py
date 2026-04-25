from __future__ import annotations

import pytest

from fuggers_py._core import Date, Tenor
from fuggers_py.curves import DiscountingCurve, YieldCurve
from tests.helpers._rates_helpers import flat_curve


@pytest.mark.parametrize(
    "bumped_curve",
    [
        pytest.param(
            lambda curve: curve.shifted(shift=0.0001),
            id="shifted",
        ),
        pytest.param(
            lambda curve: curve.bumped(
                tenor_grid=(Tenor.parse("2Y"), Tenor.parse("5Y"), Tenor.parse("10Y")),
                bumps={Tenor.parse("5Y"): 0.0001},
            ),
            id="bumped",
        ),
    ],
)
def test_bumped_curves_are_discounting_curves_with_base_identity(bumped_curve) -> None:
    base_curve = flat_curve(Date.from_ymd(2026, 4, 9), "0.03")

    curve = bumped_curve(base_curve)

    assert isinstance(curve, DiscountingCurve)
    assert not isinstance(curve, YieldCurve)
    assert curve.spec is base_curve.spec
    assert curve.reference_date == base_curve.reference_date
    assert curve.zero_rate_at(1.0) == curve.rate_at(1.0)
    assert curve.max_t() == base_curve.max_t()
    assert not hasattr(curve, "calibration_report")
