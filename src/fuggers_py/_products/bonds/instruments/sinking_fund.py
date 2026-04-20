"""Sinking-fund bond instruments.

Sinking-fund factors represent the remaining principal fraction outstanding
after each scheduled amortization date. Coupon rates are raw decimal rates and
principal amortization is generated from the remaining-factor schedule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.errors import InvalidBondSpec
from fuggers_py._core.stub_rules import StubPeriodRules
from fuggers_py._core.types import Currency, Date, Frequency, Price
from fuggers_py._core.yield_convention import AccruedConvention
from fuggers_py._math import SolverConfig, brent
from fuggers_py._math.errors import ConvergenceFailed, InvalidBracket
from fuggers_py._products.instruments import KindedInstrumentMixin

from ..cashflows import AccruedInterestCalculator, AccruedInterestInputs, CashFlowGenerator, Schedule, ScheduleConfig
from ..traits import Bond, BondAnalytics, BondCashFlow, CashFlowType
from fuggers_py._core import YieldCalculationRules
from fuggers_py._reference.bonds.types import BondIdentifiers


def _to_decimal(value: object, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class SinkingFundEntry:
    """One scheduled sinking-fund factor reset.

    Parameters
    ----------
    payment_date:
        Date on which the remaining principal factor changes.
    factor:
        Remaining principal fraction after the payment date.
    """

    payment_date: Date
    factor: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "factor", _to_decimal(self.factor, field_name="factor"))
        if self.factor < 0 or self.factor > 1:
            raise InvalidBondSpec(reason="SinkingFundEntry.factor must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class SinkingFundSchedule:
    """Ordered sinking-fund factors with non-increasing outstanding principal.

    Parameters
    ----------
    entries:
        Sinking-fund factor resets in payment-date order.
    """

    entries: tuple[SinkingFundEntry, ...]

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.entries, key=lambda entry: entry.payment_date))
        if not ordered:
            raise InvalidBondSpec(reason="SinkingFundSchedule requires at least one entry.")
        previous_factor = Decimal(1)
        for entry in ordered:
            if entry.factor > previous_factor:
                raise InvalidBondSpec(reason="Sinking fund factors must be non-increasing.")
            previous_factor = entry.factor
        object.__setattr__(self, "entries", ordered)

    @classmethod
    def new(cls, entries: list[SinkingFundEntry]) -> "SinkingFundSchedule":
        """Create a sinking-fund schedule from the supplied entries."""
        return cls(entries=tuple(entries))

    def factor_on(self, date: Date) -> Decimal:
        """Return the remaining principal factor in force on ``date``."""
        factor = Decimal(1)
        for entry in self.entries:
            if date >= entry.payment_date:
                factor = entry.factor
            else:
                break
        return factor

    def factor_for_payment(self, payment_date: Date, *, default: Decimal = Decimal(0)) -> Decimal:
        """Return the factor applied on the payment date, if scheduled."""
        for entry in self.entries:
            if entry.payment_date == payment_date:
                return entry.factor
        return default

    def to_amortization(self, *, notional: Decimal) -> list[tuple[Date, Decimal]]:
        """Convert remaining-principal factors into principal amortization cash flows."""
        amortization: list[tuple[Date, Decimal]] = []
        prior_factor = Decimal(1)
        for entry in self.entries:
            principal = (prior_factor - entry.factor) * notional
            amortization.append((entry.payment_date, principal))
            prior_factor = entry.factor
        return amortization


@dataclass(frozen=True, slots=True)
class SinkingFundBond(KindedInstrumentMixin, BondAnalytics, Bond):
    """Fixed-rate bond with scheduled principal amortization.

    Parameters
    ----------
    _issue_date, _maturity_date:
        Bond issue and maturity dates.
    _coupon_rate:
        Fixed coupon rate as a raw decimal.
    _frequency:
        Coupon frequency used to build the schedule.
    _sinking_schedule:
        Remaining-principal factor schedule.
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
    """

    KIND: ClassVar[str] = "bond.sinking_fund"

    _issue_date: Date
    _maturity_date: Date
    _coupon_rate: Decimal
    _frequency: Frequency
    _sinking_schedule: SinkingFundSchedule
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
            raise InvalidBondSpec(reason="SinkingFundBond requires a non-zero coupon frequency.")
        if self._notional <= 0:
            raise InvalidBondSpec(reason="notional must be positive.")
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
        cashflows = self._build_cashflows(schedule)
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
        sinking_schedule: SinkingFundSchedule,
        currency: Currency = Currency.USD,
        notional: Decimal = Decimal(100),
        identifiers: BondIdentifiers | None = None,
        rules: YieldCalculationRules | None = None,
        stub_rules: StubPeriodRules | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> "SinkingFundBond":
        """Construct a sinking-fund bond from its contractual inputs."""
        return cls(
            _issue_date=issue_date,
            _maturity_date=maturity_date,
            _coupon_rate=coupon_rate,
            _frequency=frequency,
            _sinking_schedule=sinking_schedule,
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

    def sinking_schedule(self) -> SinkingFundSchedule:
        return self._sinking_schedule

    def cash_flows(self, from_date: Date | None = None) -> list[BondCashFlow]:
        return CashFlowGenerator.future_cashflows(self._cashflows, from_date)

    def accrued_interest(self, settlement_date: Date) -> Decimal:
        """Return accrued interest adjusted for the outstanding sinking factor."""
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
            factor = self.factor_on(accrual_start)
            coupon_amount = self._notional * factor * self._coupon_rate * day_count.year_fraction(accrual_start, accrual_end)
            coupon_date = adjusted[i]
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

    def factor_on(self, date: Date) -> Decimal:
        """Return the remaining principal factor on ``date``."""
        return self._sinking_schedule.factor_on(date)

    def amortization_schedule(self) -> list[tuple[Date, Decimal]]:
        """Return scheduled principal reductions in currency or face units."""
        return self._sinking_schedule.to_amortization(notional=self._notional)

    def average_life(self, *, as_of_date: Date | None = None) -> Decimal:
        """Return the weighted-average time to remaining principal payments, in years."""
        anchor = as_of_date or self.issue_date()
        amortization = [(date, amount) for date, amount in self.amortization_schedule() if date > anchor and amount > 0]
        remaining_principal = sum(amount for _, amount in amortization)
        if remaining_principal == 0:
            return Decimal(0)
        weighted_years = Decimal(0)
        for payment_date, principal_amount in amortization:
            years = Decimal(str(float(anchor.days_between(payment_date)) / 365.0))
            weighted_years += years * principal_amount
        return weighted_years / remaining_principal

    def yield_to_average_life(self, clean_price: object, settlement_date: Date) -> Decimal:
        """Return the raw decimal yield implied by the average-life cash flows."""
        price = clean_price if isinstance(clean_price, Price) else Price.new(clean_price, self.currency())
        dirty_price = price.as_percentage() + self.accrued_interest(settlement_date)
        cashflows = [cf for cf in self.cash_flows(settlement_date)]
        if not cashflows:
            raise InvalidBondSpec(reason="No future cash flows remain for yield calculation.")

        day_count = self.rules().yield_day_count_obj()
        compounding = self.rules().compounding

        def objective(y: float) -> float:
            pv = 0.0
            for cf in cashflows:
                years = float(day_count.year_fraction(settlement_date, cf.date))
                pv += float(cf.factored_amount()) * compounding.discount_factor(y, years)
            return pv - float(dirty_price)

        config = SolverConfig(tolerance=1e-10, max_iterations=200)
        for lower, upper in [(-0.5, 0.5), (-0.9, 1.0), (-0.99, 2.0)]:
            try:
                result = brent(objective, lower, upper, config=config)
                return Decimal(str(result.root))
            except (ConvergenceFailed, InvalidBracket):
                continue
        raise InvalidBondSpec(reason="yield_to_average_life failed to converge.")

    def _build_cashflows(self, schedule: Schedule) -> list[BondCashFlow]:
        """Build coupon and principal cash flows using the sinking-fund factors."""
        rules = self.rules()
        day_count = rules.accrual_day_count_obj()
        flows: list[BondCashFlow] = []
        outstanding_factor = Decimal(1)
        for index in range(1, len(schedule.unadjusted_dates)):
            accrual_start = schedule.unadjusted_dates[index - 1]
            accrual_end = schedule.unadjusted_dates[index]
            pay_date = schedule.dates[index]
            accrual_factor = day_count.year_fraction(accrual_start, accrual_end)
            coupon_amount = self._notional * outstanding_factor * self._coupon_rate * accrual_factor
            ending_factor = self._sinking_schedule.factor_for_payment(
                accrual_end,
                default=Decimal(0) if accrual_end == self._maturity_date else outstanding_factor,
            )
            principal_amount = self._notional * (outstanding_factor - ending_factor)
            amount = coupon_amount + principal_amount
            flow_type = (
                CashFlowType.COUPON_AND_PRINCIPAL if principal_amount > 0 else CashFlowType.COUPON
            )
            flows.append(
                BondCashFlow(
                    date=pay_date,
                    amount=amount,
                    flow_type=flow_type,
                    accrual_start=accrual_start,
                    accrual_end=accrual_end,
                )
            )
            outstanding_factor = ending_factor
        return flows


@dataclass(slots=True)
class SinkingFundBondBuilder:
    """Fluent builder for :class:`SinkingFundBond`.

    The builder collects the sinking-fund schedule alongside the standard bond
    inputs before instantiating the bond.
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
    sinking_schedule: SinkingFundSchedule | None = None
    instrument_id: InstrumentId | None = None
    _entries: list[SinkingFundEntry] = field(default_factory=list, repr=False)

    @classmethod
    def new(cls) -> "SinkingFundBondBuilder":
        return cls()

    def with_issue_date(self, date: Date) -> "SinkingFundBondBuilder":
        self.issue_date = date
        return self

    def with_maturity_date(self, date: Date) -> "SinkingFundBondBuilder":
        self.maturity_date = date
        return self

    def with_coupon_rate(self, rate: object) -> "SinkingFundBondBuilder":
        self.coupon_rate = _to_decimal(rate, field_name="coupon_rate")
        return self

    def with_frequency(self, frequency: Frequency) -> "SinkingFundBondBuilder":
        self.frequency = frequency
        return self

    def with_currency(self, currency: Currency) -> "SinkingFundBondBuilder":
        self.currency = currency
        return self

    def with_notional(self, notional: object) -> "SinkingFundBondBuilder":
        self.notional = _to_decimal(notional, field_name="notional")
        return self

    def with_identifiers(self, identifiers: BondIdentifiers) -> "SinkingFundBondBuilder":
        self.identifiers = identifiers
        return self

    def with_instrument_id(self, instrument_id: InstrumentId | str) -> "SinkingFundBondBuilder":
        self.instrument_id = InstrumentId.parse(instrument_id)
        return self

    def with_rules(self, rules: YieldCalculationRules) -> "SinkingFundBondBuilder":
        self.rules = rules
        if self.frequency is None:
            self.frequency = rules.frequency
        return self

    def with_stub_rules(self, stub_rules: StubPeriodRules) -> "SinkingFundBondBuilder":
        self.stub_rules = stub_rules
        return self

    def with_sinking_schedule(self, schedule: SinkingFundSchedule) -> "SinkingFundBondBuilder":
        self.sinking_schedule = schedule
        self._entries = list(schedule.entries)
        return self

    def add_sinking_entry(self, payment_date: Date, factor: object) -> "SinkingFundBondBuilder":
        self._entries.append(SinkingFundEntry(payment_date=payment_date, factor=_to_decimal(factor, field_name="factor")))
        self.sinking_schedule = None
        return self

    def build_schedule(self) -> SinkingFundSchedule:
        if self.sinking_schedule is not None:
            return self.sinking_schedule
        if not self._entries:
            raise InvalidBondSpec(reason="sinking_schedule is required.")
        self.sinking_schedule = SinkingFundSchedule.new(self._entries)
        return self.sinking_schedule

    def build(self) -> SinkingFundBond:
        if self.issue_date is None:
            raise InvalidBondSpec(reason="issue_date is required.")
        if self.maturity_date is None:
            raise InvalidBondSpec(reason="maturity_date is required.")
        if self.coupon_rate is None:
            raise InvalidBondSpec(reason="coupon_rate is required.")
        frequency = self.frequency or self.rules.frequency
        schedule = self.build_schedule()
        return SinkingFundBond.new(
            issue_date=self.issue_date,
            maturity_date=self.maturity_date,
            coupon_rate=self.coupon_rate,
            frequency=frequency,
            sinking_schedule=schedule,
            currency=self.currency,
            notional=self.notional,
            identifiers=self.identifiers,
            rules=self.rules,
            stub_rules=self.stub_rules,
            instrument_id=self.instrument_id,
        )


__all__ = ["SinkingFundBond", "SinkingFundBondBuilder", "SinkingFundEntry", "SinkingFundSchedule"]
