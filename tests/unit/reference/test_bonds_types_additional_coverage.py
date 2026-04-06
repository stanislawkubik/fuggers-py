from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.reference.bonds.errors import InvalidBondSpec, SettlementError
from fuggers_py.market.indices import BondIndex, IndexFixingStore
from fuggers_py.market.indices.conventions import IndexConventions
from fuggers_py.reference.bonds.types import PriceQuote, PriceQuoteConvention, RateIndex, RoundingConvention, SettlementAdjustment, SettlementRules
from fuggers_py.reference.bonds.types.amortization import AmortizationEntry, AmortizationSchedule, AmortizationType
from fuggers_py.core import Currency, Date, WeekendCalendar


def test_bond_index_fixing_and_period_fallback_paths() -> None:
    store = IndexFixingStore()
    start = Date.from_ymd(2024, 1, 1)
    end = start.add_days(1)
    store.add_fixing("SOFR", start, Decimal("0.05"))
    index = BondIndex(
        name="SOFR",
        rate_index=RateIndex.SOFR,
        currency=Currency.USD,
        conventions=IndexConventions(),
        fixing_store=store,
    )

    assert index.fixing(start) == Decimal("0.05")
    assert float(index.rate_for_period(start, end, fallback_rate=Decimal("0.051"))) == pytest.approx(0.05)
    assert (
        BondIndex(name="SOFR", currency=Currency.USD).rate_for_period(
            start,
            end,
            fallback_rate=Decimal("0.051"),
        )
        == Decimal("0.051")
    )

    with pytest.raises(KeyError):
        BondIndex(name="SOFR", currency=Currency.USD).rate_for_period(start, end)


def test_price_quote_amortization_and_rounding_helpers_cover_conversion_paths() -> None:
    percent_quote = PriceQuote(Decimal("99.25"), PriceQuoteConvention.PERCENT_OF_PAR)
    decimal_quote = PriceQuote(Decimal("0.9925"), PriceQuoteConvention.DECIMAL_OF_PAR)

    assert percent_quote.as_decimal() == Decimal("0.9925")
    assert decimal_quote.as_percentage() == Decimal("99.2500")

    amount_entry = AmortizationEntry(date=Date.from_ymd(2025, 1, 1), amount=Decimal("12.5"))
    factor_entry = AmortizationEntry(date=Date.from_ymd(2026, 1, 1), factor=Decimal("0.80"))
    schedule = AmortizationSchedule.new(
        [factor_entry, amount_entry],
        amortization_type=AmortizationType.SINKING_FUND,
    )

    assert amount_entry.principal_reduction(Decimal("10")) == Decimal("10")
    assert factor_entry.principal_reduction(Decimal("100")) == Decimal("20")
    assert schedule.outstanding_notional(Decimal("100"), on_date=Date.from_ymd(2025, 6, 1)) == Decimal("87.5")
    assert schedule.outstanding_notional(Decimal("100")) == Decimal("70.0")

    assert RoundingConvention.none().apply(1.234) == pytest.approx(1.234)
    assert RoundingConvention.decimal_places(2).apply(1.234) == pytest.approx(1.23)

    with pytest.raises(InvalidBondSpec):
        RoundingConvention.decimal_places(-1)


def test_settlement_rules_presets_adjustments_and_same_day_restriction() -> None:
    calendar = WeekendCalendar()
    trade_date = Date.from_ymd(2024, 3, 1)

    assert SettlementAdjustment.NONE.to_business_day_convention() is None
    assert SettlementRules.us_treasury().days == 1
    assert SettlementRules.us_corporate().days == 2
    assert SettlementRules.uk_gilt().days == 1
    assert SettlementRules.german_bund().days == 2
    assert SettlementRules.eurobond().days == 2
    assert SettlementRules(days=2, use_business_days=False).settlement_date(trade_date, calendar) == Date.from_ymd(2024, 3, 4)

    with pytest.raises(SettlementError):
        SettlementRules(days=0, allow_same_day=False).settlement_date(trade_date, calendar)
