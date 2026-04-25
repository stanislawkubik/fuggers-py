from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date, Frequency, InstrumentId
from fuggers_py.bonds import CallableBondBuilder, FixedBond, FloatingRateNote, SinkingFundBond, TipsBond, ZeroCouponBond
from fuggers_py.bonds.instruments import SinkingFundEntry, SinkingFundSchedule
from fuggers_py.rates.instruments import Instrument
from fuggers_py.bonds.types import RateIndex
from fuggers_py._core import YieldCalculationRules
from fuggers_py.inflation import USD_CPI_U_NSA


def _annual_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL)


def _quarterly_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_treasury(), frequency=Frequency.QUARTERLY)


def _semi_annual_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_treasury(), frequency=Frequency.SEMI_ANNUAL)


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("properties")
def test_bond_identity_normalization_and_kind_invariants_hold_across_families() -> None:
    issue_date = Date.from_ymd(2024, 1, 1)
    sinking_schedule = SinkingFundSchedule.new(
        [
            SinkingFundEntry(issue_date.add_years(1), Decimal("0.75")),
            SinkingFundEntry(issue_date.add_years(2), Decimal("0.50")),
            SinkingFundEntry(issue_date.add_years(3), Decimal("0.25")),
            SinkingFundEntry(issue_date.add_years(4), Decimal("0.00")),
        ]
    )
    fixed = FixedBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2029, 1, 15),
        coupon_rate=Decimal("0.045"),
        frequency=Frequency.ANNUAL,
        currency=Currency.USD,
        rules=_annual_rules(),
        instrument_id="PROP-FIXED",
    )
    zero = ZeroCouponBond(
        _issue_date=Date.from_ymd(2024, 1, 15),
        _maturity_date=Date.from_ymd(2027, 1, 15),
        _currency=Currency.USD,
        _notional=Decimal("100"),
        _rules=YieldCalculationRules.us_treasury(),
        instrument_id="PROP-ZERO",
    )
    floating = FloatingRateNote.new(
        issue_date=Date.from_ymd(2025, 1, 15),
        maturity_date=Date.from_ymd(2028, 1, 15),
        index=RateIndex.SOFR,
        quoted_spread=Decimal("0.0125"),
        frequency=Frequency.QUARTERLY,
        currency=Currency.USD,
        rules=_quarterly_rules(),
        current_reference_rate=Decimal("0.041"),
        instrument_id="PROP-FRN",
    )
    tips = TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2026, 1, 15),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        dated_date=Date.from_ymd(2024, 1, 15),
        base_reference_date=Date.from_ymd(2024, 1, 15),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
        rules=_semi_annual_rules(),
        instrument_id="PROP-TIPS",
    )
    sinking = SinkingFundBond.new(
        issue_date=issue_date,
        maturity_date=issue_date.add_years(4),
        coupon_rate=Decimal("0.04"),
        frequency=Frequency.ANNUAL,
        sinking_schedule=sinking_schedule,
        rules=_annual_rules(),
        instrument_id="PROP-SINK",
    )
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(fixed)
        .add_call(call_date=Date.from_ymd(2027, 1, 15), call_price=Decimal("101"))
        .build()
    )

    for bond in (fixed, zero, floating, tips, sinking, callable_bond):
        assert isinstance(bond, Instrument)
        assert isinstance(bond.instrument_id, InstrumentId)
        assert bond.kind == type(bond).KIND

    assert callable_bond.instrument_id == fixed.instrument_id
