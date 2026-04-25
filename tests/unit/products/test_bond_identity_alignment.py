from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date, Frequency, InstrumentId
from fuggers_py.bonds import (
    CallableBond,
    CallableBondBuilder,
    FixedBond,
    FixedBondBuilder,
    FloatingRateNote,
    FloatingRateNoteBuilder,
    SinkingFundBond,
    SinkingFundBondBuilder,
    TipsBond,
    ZeroCouponBond,
)
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


def _fixed_bond(*, instrument_id: str = "BOND-FIXED") -> FixedBond:
    return FixedBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2029, 1, 15),
        coupon_rate=Decimal("0.045"),
        frequency=Frequency.ANNUAL,
        currency=Currency.USD,
        rules=_annual_rules(),
        instrument_id=instrument_id,
    )


def _zero_coupon_bond(*, instrument_id: str = "BOND-ZERO") -> ZeroCouponBond:
    return ZeroCouponBond(
        _issue_date=Date.from_ymd(2024, 1, 15),
        _maturity_date=Date.from_ymd(2027, 1, 15),
        _currency=Currency.USD,
        _notional=Decimal("100"),
        _rules=YieldCalculationRules.us_treasury(),
        instrument_id=instrument_id,
    )


def _floating_rate_note(*, instrument_id: str = "BOND-FRN") -> FloatingRateNote:
    return FloatingRateNote.new(
        issue_date=Date.from_ymd(2025, 1, 15),
        maturity_date=Date.from_ymd(2028, 1, 15),
        index=RateIndex.SOFR,
        quoted_spread=Decimal("0.0125"),
        frequency=Frequency.QUARTERLY,
        currency=Currency.USD,
        rules=_quarterly_rules(),
        current_reference_rate=Decimal("0.041"),
        instrument_id=instrument_id,
    )


def _tips_bond(*, instrument_id: str = "BOND-TIPS") -> TipsBond:
    return TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2026, 1, 15),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        dated_date=Date.from_ymd(2024, 1, 15),
        base_reference_date=Date.from_ymd(2024, 1, 15),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
        rules=_semi_annual_rules(),
        instrument_id=instrument_id,
    )


def _sinking_schedule(issue_date: Date) -> SinkingFundSchedule:
    return SinkingFundSchedule.new(
        [
            SinkingFundEntry(issue_date.add_years(1), Decimal("0.75")),
            SinkingFundEntry(issue_date.add_years(2), Decimal("0.50")),
            SinkingFundEntry(issue_date.add_years(3), Decimal("0.25")),
            SinkingFundEntry(issue_date.add_years(4), Decimal("0.00")),
        ]
    )


def _sinking_fund_bond(*, instrument_id: str = "BOND-SINK") -> SinkingFundBond:
    issue_date = Date.from_ymd(2024, 1, 1)
    return SinkingFundBond.new(
        issue_date=issue_date,
        maturity_date=issue_date.add_years(4),
        coupon_rate=Decimal("0.04"),
        frequency=Frequency.ANNUAL,
        sinking_schedule=_sinking_schedule(issue_date),
        rules=_annual_rules(),
        instrument_id=instrument_id,
    )


def _callable_bond(*, instrument_id: str = "BOND-CALL") -> CallableBond:
    return (
        CallableBondBuilder.new()
        .with_base_bond(_fixed_bond(instrument_id=instrument_id))
        .add_call(call_date=Date.from_ymd(2027, 1, 15), call_price=Decimal("101"))
        .build()
    )


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("unit")
@pytest.mark.parametrize(
    ("builder", "expected_kind"),
    [
        pytest.param(_fixed_bond, "bond.fixed", id="fixed"),
        pytest.param(_zero_coupon_bond, "bond.zero_coupon", id="zero_coupon"),
        pytest.param(_floating_rate_note, "bond.floating", id="floating_rate"),
        pytest.param(_tips_bond, "bond.tips", id="tips"),
        pytest.param(_sinking_fund_bond, "bond.sinking_fund", id="sinking_fund"),
        pytest.param(_callable_bond, "bond.callable", id="callable"),
    ],
)
def test_bond_families_expose_exact_kind_and_structural_instrument_identity(builder, expected_kind: str) -> None:
    bond = builder()

    assert type(bond).KIND == expected_kind
    assert bond.kind == expected_kind
    assert isinstance(bond, Instrument)
    assert isinstance(bond.instrument_id, InstrumentId)


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("unit")
def test_builder_round_trips_preserve_bond_instrument_ids() -> None:
    fixed = (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 15))
        .with_maturity_date(Date.from_ymd(2029, 1, 15))
        .with_coupon_rate("0.045")
        .with_frequency(Frequency.ANNUAL)
        .with_rules(_annual_rules())
        .with_instrument_id("BUILDER-FIXED")
        .build()
    )
    frn = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(Date.from_ymd(2025, 1, 15))
        .with_maturity_date(Date.from_ymd(2028, 1, 15))
        .with_index(RateIndex.SOFR)
        .with_quoted_spread("0.0125")
        .with_frequency(Frequency.QUARTERLY)
        .with_rules(_quarterly_rules())
        .with_instrument_id("BUILDER-FRN")
        .build()
    )
    issue_date = Date.from_ymd(2024, 1, 1)
    sinking = (
        SinkingFundBondBuilder.new()
        .with_issue_date(issue_date)
        .with_maturity_date(issue_date.add_years(4))
        .with_coupon_rate("0.04")
        .with_frequency(Frequency.ANNUAL)
        .with_rules(_annual_rules())
        .with_instrument_id("BUILDER-SINK")
        .add_sinking_entry(issue_date.add_years(1), "0.75")
        .add_sinking_entry(issue_date.add_years(2), "0.50")
        .add_sinking_entry(issue_date.add_years(3), "0.25")
        .add_sinking_entry(issue_date.add_years(4), "0.00")
        .build()
    )

    assert fixed.instrument_id == InstrumentId("BUILDER-FIXED")
    assert frn.instrument_id == InstrumentId("BUILDER-FRN")
    assert sinking.instrument_id == InstrumentId("BUILDER-SINK")


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("unit")
def test_callable_bond_uses_wrapped_base_bond_identity() -> None:
    callable_bond = _callable_bond()

    assert callable_bond.instrument_id == InstrumentId("BOND-CALL")
    assert callable_bond.base_bond.instrument_id == callable_bond.instrument_id
