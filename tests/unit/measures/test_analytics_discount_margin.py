from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.bonds import AnalyticsError
from fuggers_py.bonds.spreads import DiscountMarginCalculator, simple_margin, z_discount_margin
from fuggers_py.bonds.instruments import FloatingRateNoteBuilder
from fuggers_py.bonds.types import RateIndex
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Date, Frequency
from tests.helpers._rates_helpers import flat_curve


def _quarterly_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_corporate(), frequency=Frequency.QUARTERLY)


def _curves(ref: Date):
    discount_curve = flat_curve(ref, "0.03")
    forward_curve = discount_curve
    return forward_curve, discount_curve


def _sample_frn(*, cap: Decimal | None = None, floor: Decimal | None = None):
    ref = Date.from_ymd(2024, 1, 1)
    frn = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(ref)
        .with_maturity_date(ref.add_years(2))
        .with_index(RateIndex.SOFR)
        .with_quoted_spread(Decimal("0.0025"))
        .with_current_reference_rate(Decimal("0.03"))
        .with_frequency(Frequency.QUARTERLY)
        .with_rules(_quarterly_rules())
    )
    if cap is not None:
        frn = frn.with_cap(cap)
    if floor is not None:
        frn = frn.with_floor(floor)
    return ref, frn.build()


def test_dm_roundtrip_50bps() -> None:
    ref, frn = _sample_frn()
    forward_curve, discount_curve = _curves(ref)
    calculator = DiscountMarginCalculator(forward_curve, discount_curve)

    dm = Decimal("0.005")
    dirty_price = calculator.price_with_dm(frn, dm, ref)
    recovered = calculator.calculate(frn, dirty_price, ref)

    assert float(recovered) == pytest.approx(float(dm), abs=1e-8)


def test_dm_roundtrip_various_levels() -> None:
    ref, frn = _sample_frn()
    forward_curve, discount_curve = _curves(ref)
    calculator = DiscountMarginCalculator(forward_curve, discount_curve)

    for dm in [Decimal("-0.0025"), Decimal("0.0"), Decimal("0.01")]:
        dirty_price = calculator.price_with_dm(frn, dm, ref)
        recovered = calculator.calculate(frn, dirty_price, ref)
        assert float(recovered) == pytest.approx(float(dm), abs=1e-7)


def test_spread_dv01() -> None:
    ref, frn = _sample_frn()
    forward_curve, discount_curve = _curves(ref)
    calculator = DiscountMarginCalculator(forward_curve, discount_curve)

    dv01 = calculator.spread_dv01(frn, Decimal("0.005"), ref)
    assert dv01 > 0


def test_spread_duration() -> None:
    ref, frn = _sample_frn()
    forward_curve, discount_curve = _curves(ref)
    calculator = DiscountMarginCalculator(forward_curve, discount_curve)

    dm = Decimal("0.005")
    duration = calculator.spread_duration(frn, dm, ref)
    price = calculator.price_with_dm(frn, dm, ref)
    dv01 = calculator.spread_dv01(frn, dm, ref)

    assert duration > 0
    assert float(duration) == pytest.approx(float(dv01 / (price * Decimal("0.0001"))), rel=1e-10)


def test_simple_margin() -> None:
    margin = simple_margin(Decimal("98"), Decimal("1.5"), Decimal("0.03"), 90)
    expected = ((Decimal("1.5") + (Decimal("100") - Decimal("98")) * Decimal("360") / Decimal("90")) / Decimal("99")) - Decimal("0.03")
    assert margin == expected


def test_simple_margin_par() -> None:
    assert simple_margin(Decimal("100"), Decimal("3.0"), Decimal("0.03"), 90) == Decimal("0.00")


def test_settlement_after_maturity() -> None:
    ref, frn = _sample_frn()
    forward_curve, discount_curve = _curves(ref)
    calculator = DiscountMarginCalculator(forward_curve, discount_curve)

    with pytest.raises(AnalyticsError):
        calculator.calculate(frn, Decimal("100"), frn.maturity_date().add_days(1))


def test_z_discount_margin_convenience() -> None:
    ref, frn = _sample_frn()
    forward_curve, discount_curve = _curves(ref)
    calculator = DiscountMarginCalculator(forward_curve, discount_curve)
    dirty_price = calculator.price_with_dm(frn, Decimal("0.004"), ref)

    direct = calculator.calculate(frn, dirty_price, ref)
    wrapped = z_discount_margin(
        frn,
        dirty_price,
        ref,
        forward_curve=forward_curve,
        discount_curve=discount_curve,
    )
    assert float(direct) == pytest.approx(float(wrapped), abs=1e-10)


def test_dm_with_cap() -> None:
    ref, frn = _sample_frn(cap=Decimal("0.0325"))
    forward_curve, discount_curve = _curves(ref)
    calculator = DiscountMarginCalculator(forward_curve, discount_curve)

    dm = Decimal("0.004")
    dirty_price = calculator.price_with_dm(frn, dm, ref)
    recovered = calculator.calculate(frn, dirty_price, ref)

    assert float(recovered) == pytest.approx(float(dm), abs=1e-7)


def test_dm_with_floor() -> None:
    ref, frn = _sample_frn(floor=Decimal("0.0340"))
    forward_curve, discount_curve = _curves(ref)
    calculator = DiscountMarginCalculator(forward_curve, discount_curve)

    dm = Decimal("0.006")
    dirty_price = calculator.price_with_dm(frn, dm, ref)
    recovered = calculator.calculate(frn, dirty_price, ref)

    assert float(recovered) == pytest.approx(float(dm), abs=1e-7)
