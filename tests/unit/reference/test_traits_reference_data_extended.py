from __future__ import annotations

from decimal import Decimal

from fuggers_py.bonds.types import BondType, IssuerType
from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._core import InstrumentId, YearMonth
from fuggers_py._reference import (
    BondReferenceData,
    BondFutureContractReference,
    BondFutureReferenceData,
    CdsReferenceData,
    DeliverableBondReference,
    FutureReferenceData,
    RepoReferenceData,
    SwapReferenceData,
)


def test_extended_reference_records_normalize_and_coerce_fields() -> None:
    future = BondFutureReferenceData(
        instrument_id="ust-mar26",
        currency=Currency.USD,
        delivery_month="2026-03",
        contract_size="100000",
        tick_size="0.015625",
        exchange=" cbot ",
        first_delivery_date=Date.from_ymd(2026, 3, 2),
        last_delivery_date=Date.from_ymd(2026, 3, 31),
        final_delivery_date=Date.from_ymd(2026, 4, 7),
        standard_coupon_rate="0.06",
        coupon_frequency=" semi ",
        underlying_basket=("US91282CKH3", "US91282CKJ9"),
    )
    deliverable = DeliverableBondReference(
        instrument_id="US91282CKH3",
        issue_date=Date.from_ymd(2024, 2, 15),
        maturity_date=Date.from_ymd(2034, 2, 15),
        coupon_rate="0.0425",
        currency=Currency.USD,
        frequency=" semi_annual ",
        notional="100",
        published_conversion_factor="0.8125",
    )
    swap = SwapReferenceData(
        instrument_id="usd-swap-5y",
        tenor=" 5y ",
        floating_index=" sofr ",
        fixed_frequency=Frequency.SEMI_ANNUAL,
        floating_frequency=Frequency.QUARTERLY,
        day_count=" act/360 ",
        calendar=" nyc ",
    )
    repo = RepoReferenceData(
        instrument_id="repo-ust-1w",
        currency=Currency.USD,
        collateral_currency=Currency.USD,
        term=" 1w ",
        collateral_type=" UST ",
        haircut="0.02",
        settlement_lag_days=1,
    )
    cds = CdsReferenceData(
        instrument_id="acme-cds-5y",
        reference_entity=" ACME Corp ",
        tenor=" 5y ",
        seniority=" snrfor ",
        restructuring_clause=" xr ",
        coupon="0.05",
        recovery_rate="0.4",
    )

    assert future.instrument_id == InstrumentId("ust-mar26")
    assert future.delivery_month == YearMonth(2026, 3)
    assert future.contract_size == Decimal("100000")
    assert future.tick_size == Decimal("0.015625")
    assert future.exchange == "CBOT"
    assert future.first_delivery_date == Date.from_ymd(2026, 3, 2)
    assert future.last_delivery_date == Date.from_ymd(2026, 3, 31)
    assert future.final_delivery_date == Date.from_ymd(2026, 4, 7)
    assert future.standard_coupon_rate == Decimal("0.06")
    assert future.coupon_frequency is Frequency.SEMI_ANNUAL
    assert future.underlying_basket == (InstrumentId("US91282CKH3"), InstrumentId("US91282CKJ9"))

    assert FutureReferenceData is BondFutureReferenceData
    assert BondFutureContractReference is BondFutureReferenceData
    enriched_bond_reference = BondReferenceData(
        instrument_id="US1234567890",
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.SOVEREIGN,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        coupon_rate="0.04",
        frequency=Frequency.SEMI_ANNUAL,
        amount_outstanding="1000000000",
        benchmark_flag=True,
        futures_deliverable_flags=(" ty ", " us "),
        liquidity_score="0.95",
    )
    assert deliverable.frequency is Frequency.SEMI_ANNUAL
    assert deliverable.published_conversion_factor == Decimal("0.8125")
    assert enriched_bond_reference.amount_outstanding == Decimal("1000000000")
    assert enriched_bond_reference.benchmark_flag is True
    assert enriched_bond_reference.futures_deliverable_flags == ("TY", "US")
    assert enriched_bond_reference.liquidity_score == Decimal("0.95")
    assert swap.tenor == "5Y"
    assert swap.floating_index == "SOFR"
    assert swap.day_count == "ACT/360"
    assert swap.calendar == "NYC"

    assert repo.term == "1W"
    assert repo.collateral_type == "UST"
    assert repo.haircut == Decimal("0.02")
    assert repo.settlement_lag_days == 1

    assert cds.reference_entity == "ACME Corp"
    assert cds.tenor == "5Y"
    assert cds.seniority == "SNRFOR"
    assert cds.restructuring_clause == "XR"
    assert cds.coupon == Decimal("0.05")
    assert cds.recovery_rate == Decimal("0.4")
