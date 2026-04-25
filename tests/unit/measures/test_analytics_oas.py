from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.spreads import OASCalculator
from fuggers_py.bonds.instruments import CallType, CallableBondBuilder, FixedBond
from fuggers_py.bonds.options import HullWhiteModel
from fuggers_py._core import Date, Frequency
from tests.helpers._rates_helpers import flat_curve


def _callable_setup():
    settlement = Date.from_ymd(2024, 1, 1)
    base = FixedBond.new(
        issue_date=settlement,
        maturity_date=settlement.add_years(5),
        coupon_rate=Decimal("0.05"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(call_date=settlement.add_years(2), call_price=Decimal("101"), call_type=CallType.EUROPEAN)
        .add_call(call_date=settlement.add_years(3), call_price=Decimal("100.5"), call_type=CallType.EUROPEAN)
        .build()
    )
    curve = flat_curve(settlement, "0.04")
    model = HullWhiteModel(mean_reversion=Decimal("0.03"), volatility=Decimal("0.01"), term_structure=curve)
    return settlement, callable_bond, OASCalculator(model=model)


def test_oas_roundtrip() -> None:
    settlement, callable_bond, calculator = _callable_setup()
    oas = Decimal("0.005")
    price = calculator.price_with_oas(callable_bond, oas, settlement)
    recovered = calculator.calculate(callable_bond, price, settlement)
    assert float(recovered) == pytest.approx(float(oas), abs=1e-8)


def test_effective_duration_convexity_positive() -> None:
    settlement, callable_bond, calculator = _callable_setup()
    duration = calculator.effective_duration(callable_bond, Decimal("0.005"), settlement)
    convexity = calculator.effective_convexity(callable_bond, Decimal("0.005"), settlement)
    assert duration > 0
    assert convexity > 0
    assert float(duration) < 10


def test_option_value_sign_behavior() -> None:
    settlement, callable_bond, calculator = _callable_setup()
    option_value = calculator.option_value(callable_bond, Decimal("0.005"), settlement)
    callable_price = calculator.price_with_oas(callable_bond, Decimal("0.005"), settlement)
    assert option_value > 0
    assert callable_price > 0
