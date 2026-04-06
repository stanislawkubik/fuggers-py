from __future__ import annotations

from fuggers_py.measures.cashflows import ExDividendRules, SettlementCalculator, SettlementRules, SettlementStatus
from fuggers_py.measures.cashflows.settlement import settlement_status
from fuggers_py.reference.bonds.types import CalendarId
from fuggers_py.core import Date


def test_settlement_calculator_defaults_to_weekend_only_calendar_for_simple_analytics_usage() -> None:
    calculator = SettlementCalculator(SettlementRules.us_treasury())
    trade_date = Date.from_ymd(2024, 7, 3)

    assert calculator.settlement_date(trade_date) == Date.from_ymd(2024, 7, 4)


def test_settlement_calculator_accepts_explicit_market_calendar_override() -> None:
    calculator = SettlementCalculator(
        SettlementRules.us_treasury(),
        calendar=CalendarId.sifma(),
    )
    trade_date = Date.from_ymd(2024, 7, 3)

    assert calculator.settlement_date(trade_date) == Date.from_ymd(2024, 7, 5)


def test_settlement_status_covers_after_maturity_normal_and_ex_dividend_paths() -> None:
    next_coupon = Date.from_ymd(2024, 1, 15)

    assert settlement_status(Date.from_ymd(2024, 1, 16), None) is SettlementStatus.AFTER_MATURITY
    assert settlement_status(Date.from_ymd(2024, 1, 7), next_coupon) is SettlementStatus.NORMAL
    assert settlement_status(
        Date.from_ymd(2024, 1, 7),
        next_coupon,
        ex_dividend_rules=ExDividendRules(ex_dividend_days=0),
    ) is SettlementStatus.NORMAL
    assert settlement_status(
        Date.from_ymd(2024, 1, 7),
        next_coupon,
        ex_dividend_rules=ExDividendRules.uk_gilt(),
    ) is SettlementStatus.NORMAL
    assert settlement_status(
        Date.from_ymd(2024, 1, 8),
        next_coupon,
        ex_dividend_rules=ExDividendRules.uk_gilt(),
    ) is SettlementStatus.EX_DIVIDEND
