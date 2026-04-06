from __future__ import annotations

from decimal import Decimal

from fuggers_py.market.indices import (
    BondIndex,
    IndexConventions,
    IndexFixingStore,
    OvernightCompounding,
)
from fuggers_py.products.bonds.instruments import FloatingRateNoteBuilder
from fuggers_py.reference.bonds.types import RateIndex, YieldCalculationRules
from fuggers_py.core import Currency, Date, Frequency


def _sofr_store() -> IndexFixingStore:
    store = IndexFixingStore()
    start = Date.from_ymd(2024, 1, 1)
    for offset, rate in enumerate(["0.0500", "0.0505", "0.0510", "0.0515", "0.0520"], start=0):
        store.add_fixing("SOFR", start.add_days(offset), Decimal(rate))
    return store


def test_index_fixing_store_compounds_overnight_rates() -> None:
    store = _sofr_store()
    conventions = IndexConventions(overnight_compounding=OvernightCompounding.COMPOUNDED)
    rate = store.rate_for_period("SOFR", Date.from_ymd(2024, 1, 1), Date.from_ymd(2024, 1, 6), conventions=conventions)
    assert Decimal("0.04") < rate < Decimal("0.06")


def test_bond_index_and_floating_rate_note_can_consume_fixings() -> None:
    store = _sofr_store()
    index = BondIndex(name="SOFR", rate_index=RateIndex.SOFR, currency=Currency.USD, fixing_store=store)
    note = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2025, 1, 1))
        .with_index(RateIndex.SOFR)
        .with_index_definition(index)
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_quoted_spread(Decimal("0.0025"))
        .with_rules(YieldCalculationRules.us_treasury())
        .with_current_reference_rate(Decimal("0.05"))
        .build()
    )

    flows = note.cash_flows_with_fixings(store, settlement_date=Date.from_ymd(2024, 1, 1))
    assert flows
    assert all(flow.reference_rate is not None for flow in flows[:1])
    assert flows[0].reference_rate >= Decimal("0.05")
