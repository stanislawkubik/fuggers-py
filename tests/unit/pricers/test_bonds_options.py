from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py._core import OptionType
from fuggers_py.bonds.instruments import FixedBond
from fuggers_py.bonds.options import BondOption, ExerciseStyle, HullWhiteModel
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Date, Frequency
from tests.helpers._rates_helpers import flat_curve


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
    return flat_curve(ref, "0.035")


def test_bond_option_still_prices_on_hull_white_tree() -> None:
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

    assert option.price() >= Decimal(0)
