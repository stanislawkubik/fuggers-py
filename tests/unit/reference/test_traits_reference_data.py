from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.core import InstrumentId
from fuggers_py.reference import (
    BondReferenceData,
    BondType,
    CallScheduleEntry,
    FloatingRateTerms,
    IssuerType,
)


def test_reference_data_fixed_callable_and_floating_variants() -> None:
    fixed = BondReferenceData(
        instrument_id=InstrumentId("FIXED"),
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.045"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    assert fixed.to_instrument().maturity_date() == Date.from_ymd(2031, 1, 15)

    callable_ref = BondReferenceData(
        instrument_id=InstrumentId("CALL"),
        bond_type=BondType.CALLABLE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2023, 1, 15),
        maturity_date=Date.from_ymd(2033, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.05"),
        frequency=Frequency.SEMI_ANNUAL,
        call_schedule=(CallScheduleEntry(Date.from_ymd(2028, 1, 15), Decimal("100")),),
    )
    assert callable_ref.call_schedule
    assert callable_ref.to_instrument().call_schedule is not None

    frn = BondReferenceData(
        instrument_id=InstrumentId("FRN"),
        bond_type=BondType.FLOATING_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2025, 1, 15),
        maturity_date=Date.from_ymd(2028, 1, 15),
        floating_rate_terms=FloatingRateTerms(
            index_name="SOFR",
            spread=Decimal("0.0125"),
            reset_frequency=Frequency.QUARTERLY,
            current_reference_rate=Decimal("0.041"),
        ),
    )
    built_frn = frn.to_instrument()
    assert built_frn.index().name == "SOFR"
    assert built_frn.quoted_spread() == Decimal("0.0125")
    assert BondType.CALLABLE.value == "CALLABLE"
    assert IssuerType.CORPORATE.value == "CORPORATE"
