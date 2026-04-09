from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date, Frequency, InstrumentId
from fuggers_py.market.quotes import BondQuote
from fuggers_py.reference import (
    BondReferenceData,
    BondType,
    CallScheduleEntry,
    FloatingRateTerms,
    IssuerType,
)


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("validation")
def test_reference_built_bonds_preserve_instrument_id_and_quote_alignment() -> None:
    fixed_reference = BondReferenceData(
        instrument_id=InstrumentId("VAL-FIXED"),
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.045"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    callable_reference = BondReferenceData(
        instrument_id=InstrumentId("VAL-CALL"),
        bond_type=BondType.CALLABLE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2023, 1, 15),
        maturity_date=Date.from_ymd(2033, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.05"),
        frequency=Frequency.SEMI_ANNUAL,
        call_schedule=(CallScheduleEntry(Date.from_ymd(2028, 1, 15), Decimal("100")),),
    )
    floating_reference = BondReferenceData(
        instrument_id=InstrumentId("VAL-FRN"),
        bond_type=BondType.FLOATING_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2025, 1, 15),
        maturity_date=Date.from_ymd(2028, 1, 15),
        currency=Currency.USD,
        floating_rate_terms=FloatingRateTerms(
            index_name="SOFR",
            spread=Decimal("0.0125"),
            reset_frequency=Frequency.QUARTERLY,
            current_reference_rate=Decimal("0.041"),
        ),
    )
    zero_reference = BondReferenceData(
        instrument_id=InstrumentId("VAL-ZERO"),
        bond_type=BondType.ZERO_COUPON,
        issuer_type=IssuerType.SOVEREIGN,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2026, 1, 15),
        currency=Currency.USD,
    )

    fixed_bond = fixed_reference.to_instrument()
    callable_bond = callable_reference.to_instrument()
    floating_bond = floating_reference.to_instrument()
    zero_bond = zero_reference.to_instrument()
    fixed_quote = BondQuote(
        instrument=fixed_bond,
        clean_price=Decimal("101.25"),
        as_of=Date.from_ymd(2026, 1, 15),
    )

    assert fixed_bond.instrument_id == fixed_reference.instrument_id == fixed_quote.instrument_id
    assert fixed_quote.instrument is fixed_bond
    assert callable_bond.instrument_id == callable_reference.instrument_id
    assert callable_bond.base_bond.instrument_id == callable_reference.instrument_id
    assert floating_bond.instrument_id == floating_reference.instrument_id
    assert zero_bond.instrument_id == zero_reference.instrument_id
