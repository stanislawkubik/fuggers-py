from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import Currency, Date
from fuggers_py._core import InstrumentId, YearMonth
from fuggers_py._reference import (
    BondFutureContractReference,
    BondFutureReferenceData,
    DeliverableBondReference,
)
from fuggers_py._pricers.rates.futures import (
    invoice_amount,
    invoice_breakdown,
    invoice_clean_price,
    invoice_price,
)
from fuggers_py._products.rates.futures import (
    DeliverableBasket,
    DeliverableBond,
    GovernmentBondFuture,
)


def test_government_bond_future_and_basket_build_from_reference_records() -> None:
    reference = BondFutureContractReference(
        instrument_id="ust-mar26",
        currency=Currency.USD,
        delivery_month="2026-03",
        first_delivery_date=Date.from_ymd(2026, 3, 2),
        last_delivery_date=Date.from_ymd(2026, 3, 31),
        contract_size="100000",
        tick_size="0.015625",
        exchange=" cbot ",
        standard_coupon_rate="0.06",
        coupon_frequency=" semi ",
        underlying_basket=("US91282CKH3",),
    )
    deliverable_reference = DeliverableBondReference(
        instrument_id="US91282CKH3",
        issue_date=Date.from_ymd(2024, 2, 15),
        maturity_date=Date.from_ymd(2034, 2, 15),
        coupon_rate="0.0425",
        published_conversion_factor="0.8125",
    )

    contract = GovernmentBondFuture.from_reference(reference)
    deliverable = DeliverableBond.from_reference(deliverable_reference, clean_price="111.125")
    basket = DeliverableBasket(as_of=Date.from_ymd(2026, 1, 15), deliverables=(deliverable,))

    assert BondFutureContractReference is BondFutureReferenceData
    assert contract.instrument_id == InstrumentId("ust-mar26")
    assert contract.delivery_month == YearMonth(2026, 3)
    assert contract.resolved_delivery_date() == Date.from_ymd(2026, 3, 2)
    assert contract.tick_value() == Decimal("15.625")
    assert basket.currency() is Currency.USD
    assert basket.get_deliverable("US91282CKH3").published_conversion_factor == Decimal("0.8125")
    assert deliverable.reference() == deliverable_reference


def test_invoice_helpers_convert_futures_quote_to_delivery_amount() -> None:
    breakdown = invoice_breakdown(
        contract_size="100000",
        futures_price="111.50",
        conversion_factor="0.80",
        accrued_interest="1.25",
    )

    assert invoice_clean_price("111.50", "0.80") == Decimal("89.2000")
    assert invoice_price("111.50", "0.80", "1.25") == Decimal("90.4500")
    assert invoice_amount("100000", "111.50", "0.80", "1.25") == Decimal("90450.0000")
    assert breakdown.invoice_clean_price == Decimal("89.2000")
    assert breakdown.invoice_dirty_price == Decimal("90.4500")
    assert breakdown.invoice_amount == Decimal("90450.0000")
