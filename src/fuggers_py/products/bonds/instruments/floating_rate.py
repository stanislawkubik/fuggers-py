"""Floating-rate note instruments.

Quoted spread and reference-rate inputs are stored as raw decimal rates. The
current reference rate is the fallback reset level used when a fixing or
forward curve is not available, and caps/floors are applied after the spread
is added.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar, Protocol

from fuggers_py.core.ids import InstrumentId
from fuggers_py.core.types import Currency, Date, Frequency
from fuggers_py.market.indices import BondIndex, IndexConventions, IndexFixingStore
from fuggers_py.products.instruments import KindedInstrumentMixin

from ..cashflows import AccruedInterestCalculator, AccruedInterestInputs, CashFlowGenerator, Schedule, ScheduleConfig
from fuggers_py.reference.bonds.errors import InvalidBondSpec
from ..traits import Bond, BondAnalytics, BondCashFlow, CashFlowType
from fuggers_py.reference.bonds.types import AccruedConvention, BondIdentifiers, BondType, RateIndex, StubPeriodRules, YieldCalculationRules


def _to_decimal(value: object, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


class ForwardRateSource(Protocol):
    """Forward-rate source used to project FRN coupons."""

    def reference_date(self) -> Date:
        ...


@dataclass(frozen=True, slots=True)
class FloatingRateNote(KindedInstrumentMixin, BondAnalytics, Bond):
    """Floating-rate note with optional caps, floors, and fixing support.

    Parameters
    ----------
    _issue_date, _maturity_date:
        Bond issue and maturity dates.
    _index:
        Reference rate index used for projection.
    _quoted_spread:
        Spread over the reference rate as a raw decimal.
    _frequency:
        Coupon frequency used to build the schedule.
    _currency:
        Bond currency.
    _notional:
        Face amount used to scale cash flows.
    _identifiers:
        Optional identifier set.
    _rules:
        Yield and accrual rules.
    _stub_rules:
        Optional explicit stub-period rules.
    _cap_rate, _floor_rate:
        Optional coupon bounds applied after the reference rate and spread are
        combined.
    _current_reference_rate:
        Fallback reference rate used when no fixing or forward curve is
        available.
    _index_definition:
        Optional market-data helper for resolving fixings and conventions.
    instrument_id:
        Optional stable instrument identifier.

    Notes
    -----
    Quoted spread and reference-rate inputs are raw decimal rates. The
    projected coupon uses the current reference rate plus spread, then applies
    the optional cap and floor.
    """

    KIND: ClassVar[str] = "bond.floating"

    _issue_date: Date
    _maturity_date: Date
    _index: RateIndex
    _quoted_spread: Decimal
    _frequency: Frequency
    _currency: Currency = Currency.USD
    _notional: Decimal = Decimal(100)
    _identifiers: BondIdentifiers = field(default_factory=BondIdentifiers)
    _rules: YieldCalculationRules = field(default_factory=YieldCalculationRules.us_treasury)
    _stub_rules: StubPeriodRules | None = None
    _cap_rate: Decimal | None = None
    _floor_rate: Decimal | None = None
    _current_reference_rate: Decimal = Decimal(0)
    _index_definition: BondIndex | None = None
    instrument_id: InstrumentId | None = None

    _schedule: Schedule = field(init=False, repr=False)
    _fallback_cashflows: list[BondCashFlow] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self._maturity_date <= self._issue_date:
            raise InvalidBondSpec(reason="maturity_date must be after issue_date.")
        if self._frequency.is_zero():
            raise InvalidBondSpec(reason="FloatingRateNote requires a non-zero coupon frequency.")
        if self._notional <= 0:
            raise InvalidBondSpec(reason="notional must be positive.")
        if self._cap_rate is not None and self._floor_rate is not None and self._cap_rate < self._floor_rate:
            raise InvalidBondSpec(reason="cap_rate must be greater than or equal to floor_rate.")

        rules = self.rules()
        if rules.frequency != self._frequency:
            raise InvalidBondSpec(
                reason="Bond frequency must match rules.frequency (set via YieldCalculationRules)."
            )
        stub_rules = self._stub_rules or rules.stub_rules
        schedule_config = ScheduleConfig(
            start_date=self._issue_date,
            end_date=self._maturity_date,
            frequency=self._frequency,
            calendar=rules.calendar,
            business_day_convention=rules.business_day_convention,
            end_of_month=rules.end_of_month,
            stub_rules=stub_rules,
        )
        schedule = Schedule.generate(schedule_config)
        fallback_coupon = self._apply_coupon_bounds(self._current_reference_rate + self._quoted_spread)
        fallback_cashflows = CashFlowGenerator.fixed_rate_bond_cashflows(
            schedule=schedule,
            coupon_rate=fallback_coupon,
            notional=self._notional,
            rules=rules,
        )
        object.__setattr__(self, "_schedule", schedule)
        object.__setattr__(self, "_fallback_cashflows", fallback_cashflows)

    @classmethod
    def new(
        cls,
        *,
        issue_date: Date,
        maturity_date: Date,
        index: RateIndex,
        quoted_spread: Decimal,
        frequency: Frequency,
        currency: Currency = Currency.USD,
        notional: Decimal = Decimal(100),
        identifiers: BondIdentifiers | None = None,
        rules: YieldCalculationRules | None = None,
        stub_rules: StubPeriodRules | None = None,
        cap_rate: Decimal | None = None,
        floor_rate: Decimal | None = None,
        current_reference_rate: Decimal = Decimal(0),
        index_definition: BondIndex | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> "FloatingRateNote":
        return cls(
            _issue_date=issue_date,
            _maturity_date=maturity_date,
            _index=index,
            _quoted_spread=quoted_spread,
            _frequency=frequency,
            _currency=currency,
            _notional=notional,
            _identifiers=identifiers or BondIdentifiers(),
            _rules=rules or YieldCalculationRules.us_treasury(),
            _stub_rules=stub_rules,
            _cap_rate=cap_rate,
            _floor_rate=floor_rate,
            _current_reference_rate=current_reference_rate,
            _index_definition=index_definition,
            instrument_id=instrument_id,
        )

    def identifiers(self) -> BondIdentifiers:
        return self._identifiers

    def currency(self) -> Currency:
        return self._currency

    def notional(self) -> Decimal:
        return self._notional

    def issue_date(self) -> Date:
        return self._issue_date

    def maturity_date(self) -> Date:
        return self._maturity_date

    def frequency(self) -> Frequency:
        return self._frequency

    def rules(self) -> YieldCalculationRules:
        return self._rules

    def schedule(self) -> Schedule:
        return self._schedule

    def index(self) -> RateIndex:
        return self._index

    def quoted_spread(self) -> Decimal:
        """Return the raw decimal quoted spread over the reference index."""
        return self._quoted_spread

    def cap_rate(self) -> Decimal | None:
        return self._cap_rate

    def floor_rate(self) -> Decimal | None:
        return self._floor_rate

    def current_reference_rate(self) -> Decimal:
        """Return the current or fallback reference rate as a raw decimal."""
        return self._current_reference_rate

    def index_definition(self) -> BondIndex | None:
        return self._index_definition

    def current_coupon_rate(self) -> Decimal:
        """Return the current effective coupon rate after spread and bounds."""
        return self._apply_coupon_bounds(self._current_reference_rate + self._quoted_spread)

    def bond_type(self) -> BondType:
        if self._cap_rate is not None and self._floor_rate is not None:
            return BondType.COLLARED_FRN
        if self._cap_rate is not None:
            return BondType.CAPPED_FRN
        if self._floor_rate is not None:
            return BondType.FLOORED_FRN
        return BondType.FLOATING_RATE_NOTE

    def effective_rate(self, reference_rate: object | None = None) -> Decimal:
        """Return the coupon rate implied by ``reference_rate`` plus spread."""
        base_rate = self._current_reference_rate if reference_rate is None else _to_decimal(reference_rate, field_name="reference_rate")
        return self._apply_coupon_bounds(base_rate + self._quoted_spread)

    def required_fixing_dates(
        self,
        accrual_start: Date,
        accrual_end: Date,
        *,
        index_conventions: IndexConventions | None = None,
    ) -> list[Date]:
        """Return fixing dates required to determine the accrual-period rate."""
        conventions = index_conventions or self._active_conventions()
        if conventions is None:
            return [accrual_start]
        return conventions.overnight_compounding.required_fixing_dates(
            accrual_start,
            accrual_end,
            conventions=conventions,
            calendar=self._calendar(),
        )

    def period_coupon(
        self,
        accrual_start: Date,
        accrual_end: Date,
        *,
        fixing_store: IndexFixingStore | None = None,
        forward_curve: ForwardRateSource | None = None,
        index_conventions: IndexConventions | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Return the coupon cash amount for one accrual period.

        The quoted spread is a raw decimal added to the reference rate before
        cap and floor bounds are applied.
        """
        day_count = self.rules().accrual_day_count_obj()
        reference_rate = self._reference_rate_for_period(
            accrual_start,
            accrual_end,
            forward_curve=forward_curve,
            fixing_store=fixing_store,
            index_conventions=index_conventions,
            as_of=as_of,
        )
        return self._notional * self._apply_coupon_bounds(reference_rate + self._quoted_spread) * day_count.year_fraction(
            accrual_start, accrual_end
        )

    def cash_flows(self, from_date: Date | None = None) -> list[BondCashFlow]:
        return CashFlowGenerator.future_cashflows(self._fallback_cashflows, from_date)

    def projected_cash_flows(
        self,
        forward_curve: ForwardRateSource,
        settlement_date: Date | None = None,
        *,
        fixing_store: IndexFixingStore | None = None,
        index_conventions: IndexConventions | None = None,
    ) -> list[BondCashFlow]:
        """Project future cash flows using a forward curve and available fixings."""
        rules = self.rules()
        day_count = rules.accrual_day_count_obj()
        flows: list[BondCashFlow] = []

        unadjusted = self._schedule.unadjusted_dates
        adjusted = self._schedule.dates
        for index in range(1, len(unadjusted)):
            accrual_start = unadjusted[index - 1]
            accrual_end = unadjusted[index]
            pay_date = adjusted[index]
            if settlement_date is not None and pay_date <= settlement_date:
                continue

            accrual_factor = day_count.year_fraction(accrual_start, accrual_end)
            reference_rate = self._reference_rate_for_period(
                accrual_start,
                accrual_end,
                forward_curve=forward_curve,
                fixing_store=fixing_store,
                index_conventions=index_conventions,
                as_of=None if settlement_date is None else settlement_date.add_days(-1),
            )
            coupon_rate = self._apply_coupon_bounds(reference_rate + self._quoted_spread)
            coupon_amount = self._notional * coupon_rate * accrual_factor
            is_last = index == len(unadjusted) - 1
            amount = coupon_amount + (self._notional if is_last else Decimal(0))
            flow_type = CashFlowType.COUPON_AND_PRINCIPAL if is_last else CashFlowType.COUPON
            flows.append(
                BondCashFlow(
                    date=pay_date,
                    amount=amount,
                    flow_type=flow_type,
                    accrual_start=accrual_start,
                    accrual_end=accrual_end,
                    reference_rate=reference_rate,
                )
            )
        return flows

    def cash_flows_with_fixings(
        self,
        fixing_store: IndexFixingStore,
        *,
        settlement_date: Date | None = None,
        forward_curve: ForwardRateSource | None = None,
        index_conventions: IndexConventions | None = None,
    ) -> list[BondCashFlow]:
        """Return future cash flows using stored fixings where available."""
        rules = self.rules()
        day_count = rules.accrual_day_count_obj()
        flows: list[BondCashFlow] = []

        unadjusted = self._schedule.unadjusted_dates
        adjusted = self._schedule.dates
        for index in range(1, len(unadjusted)):
            accrual_start = unadjusted[index - 1]
            accrual_end = unadjusted[index]
            pay_date = adjusted[index]
            if settlement_date is not None and pay_date <= settlement_date:
                continue
            reference_rate = self._reference_rate_for_period(
                accrual_start,
                accrual_end,
                forward_curve=forward_curve,
                fixing_store=fixing_store,
                index_conventions=index_conventions,
                as_of=None if settlement_date is None else settlement_date.add_days(-1),
            )
            coupon_rate = self._apply_coupon_bounds(reference_rate + self._quoted_spread)
            accrual_factor = day_count.year_fraction(accrual_start, accrual_end)
            coupon_amount = self._notional * coupon_rate * accrual_factor
            is_last = index == len(unadjusted) - 1
            amount = coupon_amount + (self._notional if is_last else Decimal(0))
            flow_type = CashFlowType.COUPON_AND_PRINCIPAL if is_last else CashFlowType.COUPON
            flows.append(
                BondCashFlow(
                    date=pay_date,
                    amount=amount,
                    flow_type=flow_type,
                    accrual_start=accrual_start,
                    accrual_end=accrual_end,
                    reference_rate=reference_rate,
                )
            )
        return flows

    def accrued_interest(
        self,
        settlement_date: Date,
        *,
        fixing_store: IndexFixingStore | None = None,
        forward_curve: ForwardRateSource | None = None,
        index_conventions: IndexConventions | None = None,
    ) -> Decimal:
        """Return accrued interest at settlement using the effective FRN rate."""
        if settlement_date >= self._maturity_date:
            return Decimal(0)

        rules = self.rules()
        day_count = rules.accrual_day_count_obj()
        unadjusted = self._schedule.unadjusted_dates
        adjusted = self._schedule.dates
        for i in range(1, len(unadjusted)):
            accrual_start = unadjusted[i - 1]
            accrual_end = unadjusted[i]
            if not (accrual_start < settlement_date < accrual_end):
                continue

            coupon_date = adjusted[i]
            coupon_rate = self._apply_coupon_bounds(
                self._reference_rate_for_period(
                    accrual_start,
                    accrual_end,
                    forward_curve=forward_curve,
                    fixing_store=fixing_store,
                    index_conventions=index_conventions,
                    as_of=settlement_date.add_days(-1),
                )
                + self._quoted_spread
            )
            coupon_amount = self._notional * coupon_rate * day_count.year_fraction(accrual_start, accrual_end)
            inputs = AccruedInterestInputs(
                settlement_date=settlement_date,
                accrual_start=accrual_start,
                accrual_end=accrual_end,
                coupon_amount=coupon_amount,
                coupon_date=coupon_date,
                full_coupon_amount=coupon_amount,
                period_start=accrual_start,
                period_end=accrual_end,
            )
            if rules.accrued_convention is AccruedConvention.EX_DIVIDEND:
                return AccruedInterestCalculator.ex_dividend(inputs, rules=rules)
            return AccruedInterestCalculator.standard(inputs, rules=rules)
        return Decimal(0)

    def _project_reference_rate(self, forward_curve: ForwardRateSource, start: Date, end: Date) -> Decimal:
        """Project the reference rate from a curve-like source."""
        if hasattr(forward_curve, "forward_rate"):
            rate = getattr(forward_curve, "forward_rate")(start, end)
            return _to_decimal(rate, field_name="forward_rate")

        if hasattr(forward_curve, "forward_rate_at") and hasattr(forward_curve, "reference_date"):
            ref = forward_curve.date()
            tenor = float(ref.days_between(start)) / 365.0
            rate = getattr(forward_curve, "forward_rate_at")(tenor)
            return _to_decimal(rate, field_name="forward_rate_at")

        raise InvalidBondSpec(reason="forward_curve must expose forward_rate(start, end) or forward_rate_at(t).")

    def _reference_rate_for_period(
        self,
        start: Date,
        end: Date,
        *,
        forward_curve: ForwardRateSource | None = None,
        fixing_store: IndexFixingStore | None = None,
        index_conventions: IndexConventions | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Resolve the reference rate from fixings, conventions, or projection."""
        store = fixing_store or (self._index_definition.fixing_store if self._index_definition is not None else None)
        conventions = index_conventions or self._active_conventions()
        if store is not None and conventions is not None:
            try:
                return store.rate_for_period(
                    self._index.value,
                    start,
                    end,
                    conventions=conventions,
                    fallback_rate=self._current_reference_rate,
                    calendar=self._calendar(),
                    forward_curve=forward_curve,
                    as_of=as_of,
                )
            except KeyError:
                pass
        if self._index_definition is not None and store is not None:
            return self._index_definition.rate_for_period(
                start,
                end,
                store=store,
                fallback_rate=self._current_reference_rate,
            )
        if forward_curve is not None:
            return self._project_reference_rate(forward_curve, start, end)
        return self._current_reference_rate

    def _apply_coupon_bounds(self, coupon_rate: Decimal) -> Decimal:
        """Apply cap and floor bounds to a raw decimal coupon rate."""
        bounded = coupon_rate
        if self._cap_rate is not None:
            bounded = min(bounded, self._cap_rate)
        if self._floor_rate is not None:
            bounded = max(bounded, self._floor_rate)
        return bounded

    def _active_conventions(self) -> IndexConventions | None:
        if self._index_definition is None:
            return None
        return self._index_definition.conventions

    def _calendar(self):
        return self.rules().calendar.to_calendar()


@dataclass(slots=True)
class FloatingRateNoteBuilder:
    """Fluent builder for :class:`FloatingRateNote`.

    The builder resolves missing defaults from the selected rules and keeps the
    floating-rate contract inputs in one place before instantiation.
    """

    issue_date: Date | None = None
    maturity_date: Date | None = None
    index: RateIndex = RateIndex.SOFR
    quoted_spread: Decimal = Decimal(0)
    frequency: Frequency | None = None
    currency: Currency = Currency.USD
    notional: Decimal = Decimal(100)
    identifiers: BondIdentifiers = field(default_factory=BondIdentifiers)
    rules: YieldCalculationRules = field(default_factory=YieldCalculationRules.us_treasury)
    stub_rules: StubPeriodRules | None = None
    cap_rate: Decimal | None = None
    floor_rate: Decimal | None = None
    current_reference_rate: Decimal = Decimal(0)
    index_definition: BondIndex | None = None
    instrument_id: InstrumentId | None = None

    @classmethod
    def new(cls) -> "FloatingRateNoteBuilder":
        return cls()

    def with_issue_date(self, date: Date) -> "FloatingRateNoteBuilder":
        self.issue_date = date
        return self

    def with_maturity_date(self, date: Date) -> "FloatingRateNoteBuilder":
        self.maturity_date = date
        return self

    def with_index(self, index: RateIndex) -> "FloatingRateNoteBuilder":
        self.index = index
        return self

    def with_quoted_spread(self, spread: object) -> "FloatingRateNoteBuilder":
        self.quoted_spread = _to_decimal(spread, field_name="quoted_spread")
        return self

    def with_frequency(self, frequency: Frequency) -> "FloatingRateNoteBuilder":
        self.frequency = frequency
        return self

    def with_currency(self, currency: Currency) -> "FloatingRateNoteBuilder":
        self.currency = currency
        return self

    def with_notional(self, notional: object) -> "FloatingRateNoteBuilder":
        self.notional = _to_decimal(notional, field_name="notional")
        return self

    def with_identifiers(self, identifiers: BondIdentifiers) -> "FloatingRateNoteBuilder":
        self.identifiers = identifiers
        return self

    def with_instrument_id(self, instrument_id: InstrumentId | str) -> "FloatingRateNoteBuilder":
        self.instrument_id = InstrumentId.parse(instrument_id)
        return self

    def with_rules(self, rules: YieldCalculationRules) -> "FloatingRateNoteBuilder":
        self.rules = rules
        if self.frequency is None:
            self.frequency = rules.frequency
        return self

    def with_stub_rules(self, stub_rules: StubPeriodRules) -> "FloatingRateNoteBuilder":
        self.stub_rules = stub_rules
        return self

    def with_cap(self, cap_rate: object) -> "FloatingRateNoteBuilder":
        self.cap_rate = _to_decimal(cap_rate, field_name="cap_rate")
        return self

    def with_floor(self, floor_rate: object) -> "FloatingRateNoteBuilder":
        self.floor_rate = _to_decimal(floor_rate, field_name="floor_rate")
        return self

    def with_current_reference_rate(self, reference_rate: object) -> "FloatingRateNoteBuilder":
        self.current_reference_rate = _to_decimal(reference_rate, field_name="current_reference_rate")
        return self

    def with_index_definition(self, index_definition: BondIndex) -> "FloatingRateNoteBuilder":
        self.index_definition = index_definition
        return self

    def build(self) -> FloatingRateNote:
        if self.issue_date is None:
            raise InvalidBondSpec(reason="issue_date is required.")
        if self.maturity_date is None:
            raise InvalidBondSpec(reason="maturity_date is required.")
        frequency = self.frequency or self.rules.frequency
        return FloatingRateNote.new(
            issue_date=self.issue_date,
            maturity_date=self.maturity_date,
            index=self.index,
            quoted_spread=self.quoted_spread,
            frequency=frequency,
            currency=self.currency,
            notional=self.notional,
            identifiers=self.identifiers,
            rules=self.rules,
            stub_rules=self.stub_rules,
            cap_rate=self.cap_rate,
            floor_rate=self.floor_rate,
            current_reference_rate=self.current_reference_rate,
            index_definition=self.index_definition,
            instrument_id=self.instrument_id,
        )


__all__ = ["FloatingRateNote", "FloatingRateNoteBuilder", "ForwardRateSource"]
