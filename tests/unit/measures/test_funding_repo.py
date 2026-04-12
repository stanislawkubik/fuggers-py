from __future__ import annotations

import math
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.calc import FundingPricingRouter
from fuggers_py.measures.funding import repo_carry_return, repo_financing_cost, repo_net_carry
from fuggers_py.products.funding import RepoTrade
from tests.helpers._rates_helpers import flat_curve


def test_repo_trade_year_fraction_cash_interest_and_repurchase_amounts() -> None:
    start = Date.from_ymd(2026, 1, 2)
    end = start.add_days(30)
    trade = RepoTrade(
        start_date=start,
        end_date=end,
        rate="0.05",
        collateral_price="101.50",
        haircut="0.02",
        notional="1000000",
        currency="usd",
        day_count_convention="ACT_360",
        collateral_instrument_id="US91282CKH3",
    )

    expected_collateral_value = Decimal("1000000") * Decimal("101.50") / Decimal(100)
    expected_cash_lent = expected_collateral_value * Decimal("0.98")
    expected_interest = expected_cash_lent * Decimal("0.05") * (Decimal(30) / Decimal(360))

    assert trade.currency is Currency.USD
    assert trade.day_count_convention is DayCountConvention.ACT_360
    assert str(trade.collateral_instrument_id) == "US91282CKH3"
    assert trade.year_fraction() == Decimal(30) / Decimal(360)
    assert trade.collateral_market_value() == expected_collateral_value
    assert trade.haircut_amount() == expected_collateral_value * Decimal("0.02")
    assert trade.cash_lent() == expected_cash_lent
    assert trade.interest_amount() == expected_interest
    assert trade.repurchase_amount() == expected_cash_lent + expected_interest


def test_repo_carry_helpers_and_funding_router() -> None:
    start = Date.from_ymd(2026, 2, 3)
    end = start.add_days(30)
    trade = RepoTrade(
        start_date=start,
        end_date=end,
        rate=Decimal("0.03"),
        collateral_price=Decimal("100.00"),
        haircut=Decimal("0.02"),
        cash_amount=Decimal("980000"),
        currency=Currency.USD,
    )
    curve = flat_curve(start, Decimal("0.04"))

    financing_cost = repo_financing_cost(trade)
    net_carry = repo_net_carry(
        trade,
        collateral_income=Decimal("5000"),
        haircut_financing_cost=Decimal("100"),
    )
    carry_return = repo_carry_return(
        trade,
        collateral_income=Decimal("5000"),
        haircut_financing_cost=Decimal("100"),
    )
    result = FundingPricingRouter().price_repo(trade, repo_curve=curve)

    assert trade.collateral_market_value() == Decimal("1000000")
    assert financing_cost == trade.interest_amount()
    assert net_carry == Decimal("5000") - financing_cost - Decimal("100")
    assert carry_return == net_carry / trade.cash_lent()
    assert result.collateral_value == Decimal("1000000")
    assert result.haircut_amount == Decimal("20000")
    assert result.cash_lent == Decimal("980000")
    assert result.year_fraction == Decimal(30) / Decimal(360)
    assert result.curve_zero_rate == Decimal("0.04")
    assert float(result.forward_rate) == pytest.approx(
        (math.exp(0.04 * 30 / 365) - 1.0) / (30 / 360),
        abs=1e-12,
    )
    assert result.funding_spread == Decimal("-0.01")
