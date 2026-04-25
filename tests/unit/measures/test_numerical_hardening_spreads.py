from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.spreads import ProceedsAssetSwap
from fuggers_py.bonds.instruments import FixedBond
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Currency, Date, Frequency
from tests.helpers._rates_helpers import flat_curve


def test_proceeds_asset_swap_uses_settlement_normalized_swap_rate() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    settlement_date = Date.from_ymd(2025, 1, 1)
    curve = flat_curve(reference_date, "0.03")
    bond = FixedBond.new(
        issue_date=reference_date,
        maturity_date=Date.from_ymd(2027, 1, 1),
        coupon_rate=Decimal("0.04"),
        frequency=Frequency.ANNUAL,
        currency=Currency.USD,
        rules=YieldCalculationRules.eurobond(),
    )

    calculator = ProceedsAssetSwap(curve)
    dirty_price = Decimal("101.25")
    annuity = calculator._annuity(bond, settlement_date)
    start_df = curve.discount_factor(settlement_date)
    end_df = curve.discount_factor(bond.maturity_date())
    expected_swap_rate = (start_df - end_df) / (annuity * start_df)
    expected_par_par = (((Decimal("100") - dirty_price) / (annuity * Decimal("100"))) + bond.coupon_rate() - expected_swap_rate)
    expected_spread = expected_par_par * Decimal("100") / dirty_price

    assert float(calculator.calculate(bond, dirty_price, settlement_date)) == pytest.approx(
        float(expected_spread),
        rel=1e-12,
    )
