from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.reference.bonds.errors import InvalidBondSpec
from fuggers_py.market.indices import BondIndex, IndexConventions, IndexFixingStore, OvernightCompounding
from fuggers_py.products.bonds.instruments import FloatingRateNoteBuilder
from fuggers_py.reference.bonds.types import BondType, RateIndex, SOFRConvention, YieldCalculationRules
from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.market.curves import DiscountCurveBuilder


def _quarterly_treasury_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_treasury(), frequency=Frequency.QUARTERLY)


def _projection_curve(ref: Date, *, shift: Decimal = Decimal(0)):
    return (
        DiscountCurveBuilder(reference_date=ref)
        .add_zero_rate(0.25, Decimal("0.05") + shift)
        .add_zero_rate(1.0, Decimal("0.0525") + shift)
        .add_zero_rate(2.0, Decimal("0.055") + shift)
        .build()
    )


@dataclass(frozen=True, slots=True)
class _ReferenceDateForwardCurve:
    reference_date: Date
    rate: Decimal = Decimal("0.05")

    def forward_rate_at(self, tenor: float) -> Decimal:
        return self.rate


def _fixing_store(start: Date) -> IndexFixingStore:
    store = IndexFixingStore()
    for offset, rate in enumerate(
        ["0.0490", "0.0495", "0.0500", "0.0505", "0.0510", "0.0515", "0.0520", "0.0525", "0.0530"],
        start=0,
    ):
        store.add_fixing("SOFR", start.add_days(offset), Decimal(rate))
        store.add_fixing("SONIA", start.add_days(offset), Decimal(rate) - Decimal("0.0010"))
        store.add_fixing("ESTR", start.add_days(offset), Decimal(rate) - Decimal("0.0015"))
    return store


def _frn(
    ref: Date,
    *,
    index: RateIndex = RateIndex.SOFR,
    spread: str = "0.0025",
    cap: str | None = None,
    floor: str | None = None,
):
    store = _fixing_store(ref.add_days(-10))
    index_definition = BondIndex(
        name=index.value,
        rate_index=index,
        currency=Currency.USD,
        fixing_store=store,
        conventions=IndexConventions(overnight_compounding=OvernightCompounding.COMPOUNDED),
    )
    note = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(ref.add_months(-3))
        .with_maturity_date(ref.add_years(2))
        .with_index(index)
        .with_index_definition(index_definition)
        .with_frequency(Frequency.QUARTERLY)
        .with_currency(Currency.USD)
        .with_quoted_spread(Decimal(spread))
        .with_rules(_quarterly_treasury_rules())
        .with_current_reference_rate(Decimal("0.0520"))
    )
    if cap is not None:
        note = note.with_cap(Decimal(cap))
    if floor is not None:
        note = note.with_floor(Decimal(floor))
    return note.build(), store


def test_frn_builder() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, _ = _frn(ref)
    assert note.index() is RateIndex.SOFR
    assert note.frequency() is Frequency.QUARTERLY


def test_us_treasury_frn() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, _ = _frn(ref)
    assert note.current_coupon_rate() > Decimal("0.05")


def test_corporate_sofr_frn() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    rules = replace(YieldCalculationRules.us_corporate(), frequency=Frequency.QUARTERLY)
    note, _ = _frn(ref)
    note = replace(note, _rules=rules)
    assert note.rules().description == "US Corporate Bond Convention"


def test_effective_rate_with_floor() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, _ = _frn(ref, spread="-0.01", floor="0.03")
    assert note.effective_rate(Decimal("0.02")) == Decimal("0.03")


def test_effective_rate_with_cap() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, _ = _frn(ref, spread="0.01", cap="0.055")
    assert note.effective_rate(Decimal("0.05")) == Decimal("0.055")


def test_effective_rate_collar() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, _ = _frn(ref, spread="0.00", cap="0.055", floor="0.03")
    assert note.effective_rate(Decimal("0.08")) == Decimal("0.055")
    assert note.effective_rate(Decimal("0.01")) == Decimal("0.03")


def test_period_coupon() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, store = _frn(ref)
    start, end = note.schedule().unadjusted_dates[:2]
    coupon = note.period_coupon(start, end, fixing_store=store, forward_curve=_projection_curve(ref))
    assert coupon > Decimal("0")


def test_period_coupon_accepts_reference_date_forward_curve_without_date_method() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(ref.add_months(-3))
        .with_maturity_date(ref.add_years(2))
        .with_index(RateIndex.SOFR)
        .with_frequency(Frequency.QUARTERLY)
        .with_currency(Currency.USD)
        .with_quoted_spread(Decimal("0.0025"))
        .with_rules(_quarterly_treasury_rules())
        .with_current_reference_rate(Decimal("0.0520"))
        .build()
    )
    start, end = note.schedule().unadjusted_dates[:2]

    coupon = note.period_coupon(start, end, forward_curve=_ReferenceDateForwardCurve(ref))

    assert coupon > Decimal("0")


def test_bond_type_classification() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    plain, _ = _frn(ref)
    capped, _ = _frn(ref, cap="0.055")
    floored, _ = _frn(ref, floor="0.03")
    collared, _ = _frn(ref, cap="0.055", floor="0.03")
    assert plain.bond_type() is BondType.FLOATING_RATE_NOTE
    assert capped.bond_type() is BondType.CAPPED_FRN
    assert floored.bond_type() is BondType.FLOORED_FRN
    assert collared.bond_type() is BondType.COLLARED_FRN


def test_accrued_interest() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, store = _frn(ref)
    settlement = ref.add_days(20)
    accrued = note.accrued_interest(settlement, fixing_store=store, forward_curve=_projection_curve(ref))
    assert accrued > Decimal("0")


def test_cash_flows() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, store = _frn(ref)
    flows = note.projected_cash_flows(_projection_curve(ref), ref, fixing_store=store)
    assert flows
    assert flows[-1].amount > note.notional()


def test_sonia_frn() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, _ = _frn(ref, index=RateIndex.SONIA)
    assert note.index() is RateIndex.SONIA


def test_estr_frn() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, _ = _frn(ref, index=RateIndex.ESTR)
    assert note.index() is RateIndex.ESTR


def test_sofr_convention_display() -> None:
    assert SOFRConvention.COMPOUNDED_IN_ARREARS.value == "COMPOUNDED_IN_ARREARS"


def test_missing_required_fields() -> None:
    with pytest.raises(InvalidBondSpec):
        FloatingRateNoteBuilder.new().with_maturity_date(Date.from_ymd(2026, 1, 1)).build()
    with pytest.raises(InvalidBondSpec):
        FloatingRateNoteBuilder.new().with_issue_date(Date.from_ymd(2024, 1, 1)).build()


def test_invalid_dates() -> None:
    with pytest.raises(InvalidBondSpec):
        (
            FloatingRateNoteBuilder.new()
            .with_issue_date(Date.from_ymd(2025, 1, 1))
            .with_maturity_date(Date.from_ymd(2024, 1, 1))
            .with_frequency(Frequency.QUARTERLY)
            .with_rules(_quarterly_treasury_rules())
            .build()
        )


def test_accrued_interest_with_fixing_store_and_projection_curve() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note, store = _frn(ref)
    settlement = ref.add_days(20)
    low_curve = _projection_curve(ref, shift=Decimal("-0.0025"))
    high_curve = _projection_curve(ref, shift=Decimal("0.0025"))

    accrued_low = note.accrued_interest(settlement, fixing_store=store, forward_curve=low_curve)
    accrued_high = note.accrued_interest(settlement, fixing_store=store, forward_curve=high_curve)

    assert Decimal("0.1") < accrued_low < Decimal("5.0")
    assert accrued_high > accrued_low
