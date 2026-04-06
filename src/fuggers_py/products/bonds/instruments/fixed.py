"""Fixed-rate coupon bond (`fuggers_py.products.bonds.instruments.fixed`).

The instrument stores the coupon schedule, notional, currency, and yield rules
needed to generate deterministic fixed-rate cash flows and accrued interest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar

from fuggers_py.core.ids import InstrumentId
from fuggers_py.core.types import Currency, Date, Frequency
from fuggers_py.products.instruments import KindedInstrumentMixin

from ..cashflows import AccruedInterestCalculator, AccruedInterestInputs, CashFlowGenerator, Schedule, ScheduleConfig
from fuggers_py.reference.bonds.errors import InvalidBondSpec
from ..traits import Bond, BondAnalytics, BondCashFlow
from fuggers_py.reference.bonds.types import AccruedConvention, BondIdentifiers, StubPeriodRules, YieldCalculationRules


def _to_decimal(value: object, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


def _shift_reference_date(date: Date, months: int, *, preserve_eom: bool) -> Date:
    shifted = date.add_months(months)
    if preserve_eom:
        return shifted.end_of_month()
    return shifted


def _reference_period_bounds(schedule: Schedule, index: int) -> tuple[Date, Date]:
    unadjusted = schedule.unadjusted_dates
    accrual_start = unadjusted[index - 1]
    accrual_end = unadjusted[index]
    config = schedule.config
    months = config.frequency.months_per_period()
    if months <= 0:
        return accrual_start, accrual_end

    preserve_eom = config.end_of_month and (accrual_start.is_end_of_month() or accrual_end.is_end_of_month())
    first_regular = config.first_regular_date()
    if index == 1 and first_regular is not None:
        return (
            _shift_reference_date(first_regular, -months, preserve_eom=preserve_eom),
            first_regular,
        )

    penultimate = config.penultimate_date()
    if index == len(unadjusted) - 1 and penultimate is not None:
        return (
            penultimate,
            _shift_reference_date(penultimate, months, preserve_eom=preserve_eom),
        )

    return accrual_start, accrual_end


@dataclass(frozen=True, slots=True)
class FixedBond(KindedInstrumentMixin, BondAnalytics, Bond):
    """Plain fixed-rate coupon bond.

    Parameters
    ----------
    _issue_date, _maturity_date:
        Bond issue and maturity dates.
    _coupon_rate:
        Fixed coupon rate as a raw decimal.
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
    instrument_id:
        Optional stable instrument identifier.

    Notes
    -----
    Coupon rates are stored as raw decimal rates, so ``0.05`` means a 5
    percent annual coupon. Cash flows are generated from the bond's schedule
    and yield calculation rules, and accrued interest follows the configured
    accrued convention.
    """

    KIND: ClassVar[str] = "bond.fixed"

    _issue_date: Date
    _maturity_date: Date
    _coupon_rate: Decimal
    _frequency: Frequency
    _currency: Currency = Currency.USD
    _notional: Decimal = Decimal(100)
    _identifiers: BondIdentifiers = field(default_factory=BondIdentifiers)
    _rules: YieldCalculationRules = field(default_factory=YieldCalculationRules.us_treasury)
    _stub_rules: StubPeriodRules | None = None
    instrument_id: InstrumentId | None = None

    _schedule: Schedule = field(init=False, repr=False)
    _cashflows: list[BondCashFlow] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self._maturity_date <= self._issue_date:
            raise InvalidBondSpec(reason="maturity_date must be after issue_date.")
        if self._frequency.is_zero():
            raise InvalidBondSpec(reason="FixedBond requires a non-zero coupon frequency.")
        if self._notional <= 0:
            raise InvalidBondSpec(reason="notional must be positive.")
        if self._coupon_rate < Decimal("-1") or self._coupon_rate > Decimal("1"):
            raise InvalidBondSpec(reason="coupon_rate must be a decimal rate between -1 and 1.")

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
        cashflows = CashFlowGenerator.fixed_rate_bond_cashflows(
            schedule=schedule,
            coupon_rate=self._coupon_rate,
            notional=self._notional,
            rules=rules,
        )
        object.__setattr__(self, "_schedule", schedule)
        object.__setattr__(self, "_cashflows", cashflows)

    @classmethod
    def new(
        cls,
        *,
        issue_date: Date,
        maturity_date: Date,
        coupon_rate: Decimal,
        frequency: Frequency,
        currency: Currency = Currency.USD,
        notional: Decimal = Decimal(100),
        identifiers: BondIdentifiers | None = None,
        rules: YieldCalculationRules | None = None,
        stub_rules: StubPeriodRules | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> "FixedBond":
        """Construct a fixed-rate bond from its contractual inputs."""
        return cls(
            _issue_date=issue_date,
            _maturity_date=maturity_date,
            _coupon_rate=coupon_rate,
            _frequency=frequency,
            _currency=currency,
            _notional=notional,
            _identifiers=identifiers or BondIdentifiers(),
            _rules=rules or YieldCalculationRules.us_treasury(),
            _stub_rules=stub_rules,
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

    def coupon_rate(self) -> Decimal:
        return self._coupon_rate

    def rules(self) -> YieldCalculationRules:
        return self._rules

    def schedule(self) -> Schedule:
        return self._schedule

    def cash_flows(self, from_date: Date | None = None) -> list[BondCashFlow]:
        """Return future cash flows from ``from_date`` onward."""
        flows = CashFlowGenerator.future_cashflows(self._cashflows, from_date)
        return list(flows)

    def accrued_interest(self, settlement_date: Date) -> Decimal:
        """Return accrued interest at settlement in the bond's quote basis."""
        if settlement_date >= self._maturity_date:
            return Decimal(0)

        rules = self.rules()
        day_count = rules.accrual_day_count_obj()
        unadj = self._schedule.unadjusted_dates
        adj = self._schedule.dates

        for i in range(1, len(unadj)):
            accrual_start = unadj[i - 1]
            accrual_end = unadj[i]
            if not (accrual_start < settlement_date < accrual_end):
                continue

            coupon_date = adj[i]
            coupon_amount = self._notional * self._coupon_rate * day_count.year_fraction(accrual_start, accrual_end)
            period_start, period_end = _reference_period_bounds(self._schedule, i)
            inputs = AccruedInterestInputs(
                settlement_date=settlement_date,
                accrual_start=accrual_start,
                accrual_end=accrual_end,
                coupon_amount=coupon_amount,
                coupon_date=coupon_date,
                full_coupon_amount=coupon_amount,
                period_start=period_start,
                period_end=period_end,
            )

            if rules.accrued_convention is AccruedConvention.EX_DIVIDEND:
                return AccruedInterestCalculator.ex_dividend(inputs, rules=rules)
            return AccruedInterestCalculator.standard(inputs, rules=rules)

        return Decimal(0)


@dataclass(slots=True)
class FixedBondBuilder:
    """Fluent builder for :class:`FixedBond`.

    The builder accumulates contractual inputs and resolves missing defaults
    from the selected yield rules before constructing the bond.
    """

    issue_date: Date | None = None
    maturity_date: Date | None = None
    coupon_rate: Decimal | None = None
    frequency: Frequency | None = None
    currency: Currency = Currency.USD
    notional: Decimal = Decimal(100)
    identifiers: BondIdentifiers = field(default_factory=BondIdentifiers)
    rules: YieldCalculationRules = field(default_factory=YieldCalculationRules.us_treasury)
    stub_rules: StubPeriodRules | None = None
    instrument_id: InstrumentId | None = None

    @classmethod
    def new(cls) -> "FixedBondBuilder":
        return cls()

    def with_issue_date(self, date: Date) -> "FixedBondBuilder":
        self.issue_date = date
        return self

    def with_maturity_date(self, date: Date) -> "FixedBondBuilder":
        self.maturity_date = date
        return self

    def with_coupon_rate(self, rate: object) -> "FixedBondBuilder":
        self.coupon_rate = _to_decimal(rate, field_name="coupon_rate")
        return self

    def with_frequency(self, frequency: Frequency) -> "FixedBondBuilder":
        self.frequency = frequency
        return self

    def with_currency(self, currency: Currency) -> "FixedBondBuilder":
        self.currency = currency
        return self

    def with_notional(self, notional: object) -> "FixedBondBuilder":
        self.notional = _to_decimal(notional, field_name="notional")
        return self

    def with_identifiers(self, identifiers: BondIdentifiers) -> "FixedBondBuilder":
        self.identifiers = identifiers
        return self

    def with_instrument_id(self, instrument_id: InstrumentId | str) -> "FixedBondBuilder":
        self.instrument_id = InstrumentId.parse(instrument_id)
        return self

    def with_rules(self, rules: YieldCalculationRules) -> "FixedBondBuilder":
        self.rules = rules
        if self.frequency is None:
            self.frequency = rules.frequency
        return self

    def with_stub_rules(self, stub_rules: StubPeriodRules) -> "FixedBondBuilder":
        self.stub_rules = stub_rules
        return self

    def build(self) -> FixedBond:
        if self.issue_date is None:
            raise InvalidBondSpec(reason="issue_date is required.")
        if self.maturity_date is None:
            raise InvalidBondSpec(reason="maturity_date is required.")
        if self.coupon_rate is None:
            raise InvalidBondSpec(reason="coupon_rate is required.")
        freq = self.frequency or self.rules.frequency

        return FixedBond.new(
            issue_date=self.issue_date,
            maturity_date=self.maturity_date,
            coupon_rate=self.coupon_rate,
            frequency=freq,
            currency=self.currency,
            notional=self.notional,
            identifiers=self.identifiers,
            rules=self.rules,
            stub_rules=self.stub_rules,
            instrument_id=self.instrument_id,
        )


__all__ = ["FixedBond", "FixedBondBuilder"]
