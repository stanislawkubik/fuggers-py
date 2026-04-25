from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds import AnalyticsError
from fuggers_py.bonds.yields import (
    ShortDateCalculator,
    current_yield,
    current_yield_from_amount,
    current_yield_pct,
    simple_yield,
    true_yield,
)


def test_current_yield_par() -> None:
    result = current_yield(Decimal("0.05"), Decimal("100.0"))
    assert float(result) == pytest.approx(0.05, abs=1e-9)
    assert current_yield_pct(Decimal("0.05"), Decimal("100.0")) == Decimal("5")


def test_current_yield_boeing_example() -> None:
    result = current_yield(Decimal("0.075"), Decimal("110.503"))
    assert float(result) == pytest.approx(0.0679, abs=0.0002)


def test_current_yield_from_amount() -> None:
    result = current_yield_from_amount(Decimal("7.5"), Decimal("110.503"))
    assert float(result) == pytest.approx(0.0679, abs=0.0002)


def test_simple_yield_discount_bond() -> None:
    result = simple_yield(Decimal("5.0"), Decimal("95.0"), Decimal("100.0"), Decimal("5.0"))
    assert float(result) == pytest.approx(6.32, abs=0.02)


def test_simple_yield_premium_bond() -> None:
    result = simple_yield(Decimal("5.0"), Decimal("105.0"), Decimal("100.0"), Decimal("5.0"))
    assert float(result) == pytest.approx(3.81, abs=0.02)


def test_true_yield() -> None:
    result = true_yield(Decimal("0.05"), Decimal("-0.0001"))
    assert float(result) == pytest.approx(0.0499, abs=1e-10)


def test_short_date_defaults() -> None:
    calc = ShortDateCalculator.new()
    assert calc.use_money_market_below(1 / 24)
    assert calc.is_short_dated(0.5)
    assert not calc.is_short_dated(1.1)


def test_invalid_inputs_raise() -> None:
    with pytest.raises(AnalyticsError):
        current_yield(Decimal("0.05"), Decimal("0"))
    with pytest.raises(AnalyticsError):
        simple_yield(Decimal("5"), Decimal("100"), Decimal("100"), Decimal("0"))
