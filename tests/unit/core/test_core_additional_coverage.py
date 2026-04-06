from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import CashFlow, CashFlowSchedule, CashFlowType, Compounding, Currency, Date, Frequency, Price, Spread, SpreadType, Yield
from fuggers_py.core.errors import InvalidCashFlowError, InvalidDateError, InvalidPriceError, InvalidYieldError


def test_currency_frequency_and_compounding_helpers_cover_public_branches() -> None:
    assert Currency.USD.code() == "USD"
    assert Currency.USD.symbol() == "$"
    assert Currency.USD.name() == "US Dollar"
    assert str(Currency.USD) == "USD"
    assert Currency.USD.numeric_code() == 840
    assert Currency.USD.is_g10() is True
    assert Currency.INR.is_emerging() is True
    assert Currency.JPY.decimal_places() == 0
    assert Currency.USD.standard_settlement_days() == 1
    assert Currency.EUR.standard_settlement_days() == 2
    assert Currency.from_code("usd") is Currency.USD

    with pytest.raises(ValueError):
        Currency.from_code("not-a-currency")

    assert Frequency.ANNUAL.periods_per_year() == 1
    assert Frequency.SEMI_ANNUAL.months_per_period() == 6
    assert str(Frequency.SEMI_ANNUAL) == "Semi-Annual"
    assert Frequency.ZERO.is_zero() is True
    assert Compounding.SIMPLE.is_simple() is True
    assert Compounding.CONTINUOUS.is_continuous() is True
    assert str(Compounding.CONTINUOUS) == "Continuous"
    assert Compounding.DAILY.periods_per_year() == 365
    assert str(SpreadType.ASSET_SWAP_PROCEEDS) == "Asset Swap Proceeds"


def test_date_helpers_cover_boundaries_and_comparison_utilities() -> None:
    leap = Date.from_ymd(2024, 2, 29)
    march = Date.from_ymd(2024, 3, 15)

    assert leap.day_of_year() == 60
    assert leap.start_of_month() == Date.from_ymd(2024, 2, 1)
    assert leap.end_of_month() == Date.from_ymd(2024, 2, 29)
    assert leap.start_of_year() == Date.from_ymd(2024, 1, 1)
    assert leap.end_of_year() == Date.from_ymd(2024, 12, 31)
    assert leap.is_end_of_month() is True
    assert Date.min(leap, march) == leap
    assert Date.max(leap, march) == march
    assert march.weekday() == 4

    with pytest.raises(InvalidDateError):
        Date.parse("2024/02/29")

    with pytest.raises(InvalidDateError):
        leap.add_months(12 * 10000)

    with pytest.raises(InvalidDateError):
        leap.add_years(10000)


def test_price_yield_and_spread_helpers_cover_conversion_and_validation_paths() -> None:
    clean = Price.new("99.125", Currency.USD)
    dirty = clean.to_dirty("0.875")

    assert clean.is_discount() is True
    assert clean.is_premium() is False
    assert Price.par(Currency.USD).is_at_par() is True
    assert clean.discount_or_premium() == Decimal("-0.875")
    assert dirty.to_clean("0.875") == clean
    assert clean.dollar_value("250000") == Decimal("247812.500")
    assert clean.round(2).as_percentage() == Decimal("99.12")
    assert clean.same_currency(Price.par(Currency.USD)) is True

    with pytest.raises(InvalidPriceError):
        Price.new(0, Currency.USD)

    annual = Yield.from_percentage("5.0", Compounding.ANNUAL)
    assert annual.convert_to(Compounding.ANNUAL) is annual
    assert annual.convert_to(Compounding.CONTINUOUS).value() > 0

    with pytest.raises(InvalidYieldError):
        Yield.new("1.5", Compounding.ANNUAL)

    spread = Spread.new("-25.5", SpreadType.OAS)
    assert spread.is_negative() is True
    assert spread.abs().as_bps() == Decimal("25.5")
    assert spread.round(0).as_bps() == Decimal("-26")
    assert (-spread).as_bps() == Decimal("25.5")


def test_cashflow_helpers_cover_inflation_final_and_schedule_container_paths() -> None:
    start = Date.from_ymd(2024, 1, 1)
    end = Date.from_ymd(2024, 6, 30)
    pay = Date.from_ymd(2024, 6, 30)

    final_cf = CashFlow.final_payment_with_accrual(pay, "2.0", "100.0", start, end)
    inflation_coupon = CashFlow.inflation_coupon(pay, "1.2")
    inflation_principal = CashFlow.inflation_principal(pay, "100.0")

    assert final_cf.is_coupon() is True
    assert final_cf.is_principal() is True
    assert final_cf.payment_date() == pay
    assert inflation_coupon.is_inflation_linked() is True
    assert inflation_principal.is_inflation_linked() is True
    assert str(CashFlowType.CALL) == "Call"

    with pytest.raises(InvalidCashFlowError):
        CashFlow.coupon(pay, "1.0").with_accrual(end, start)

    schedule = CashFlowSchedule.with_capacity(4)
    assert schedule.is_empty() is True
    schedule.push(CashFlow.coupon(Date.from_ymd(2024, 7, 1), "1.0"))
    schedule.push(final_cf)
    schedule.sort_by_date()

    assert schedule.len() == 2
    assert len(tuple(schedule.iter())) == 2
    assert len(schedule.as_slice()) == 2
    assert schedule.after(pay).total() == Decimal("1.0")
