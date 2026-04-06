from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py.products.bonds.instruments import CallableBondBuilder, FixedBond
from fuggers_py.pricers.bonds.options import BondOption, ExerciseStyle, HullWhiteModel, OptionType
from fuggers_py.reference.bonds.types import PutType, YieldCalculationRules
from fuggers_py.core import Date, Frequency
from fuggers_py.market.curves import DiscountCurveBuilder


def _annual_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL)


def _base_bond() -> FixedBond:
    issue = Date.from_ymd(2024, 2, 20)
    return FixedBond.new(
        issue_date=issue,
        maturity_date=issue.add_years(5),
        coupon_rate=Decimal("0.05"),
        frequency=Frequency.ANNUAL,
        rules=_annual_rules(),
    )


def _curve(ref: Date):
    return (
        DiscountCurveBuilder(reference_date=ref)
        .add_zero_rate(1.0, Decimal("0.03"))
        .add_zero_rate(10.0, Decimal("0.04"))
        .build()
    )


def test_callable_bond_builder_supports_put_schedules_and_ytw() -> None:
    base = _base_bond()
    bond = (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(call_date=Date.from_ymd(2027, 2, 20), call_price=Decimal("100.5"))
        .add_put(put_date=Date.from_ymd(2026, 2, 20), put_price=Decimal("101.5"), put_type=PutType.EUROPEAN)
        .build()
    )

    settlement = Date.from_ymd(2024, 8, 1)
    clean_price = Decimal("102.00")
    ytm = bond.yield_to_maturity(clean_price, settlement)
    ytc = bond.yield_to_call(clean_price, settlement, Date.from_ymd(2027, 2, 20))
    ytp = bond.yield_to_put(clean_price, settlement, Date.from_ymd(2026, 2, 20))
    ytw = bond.yield_to_worst(clean_price, settlement)

    assert ytw == min(ytm, ytc, ytp)


def test_bond_option_prices_on_hull_white_tree() -> None:
    base = _base_bond()
    ref = Date.from_ymd(2024, 2, 20)
    model = HullWhiteModel(mean_reversion=Decimal("0.03"), volatility=Decimal("0.01"), term_structure=_curve(ref))
    option = BondOption(
        expiry=Date.from_ymd(2026, 2, 20),
        strike=Decimal("100"),
        bond=base,
        model=model,
        option_type=OptionType.CALL,
        exercise_style=ExerciseStyle.EUROPEAN,
        valuation_date=ref,
    )

    price = option.price()
    assert price >= Decimal("0")
