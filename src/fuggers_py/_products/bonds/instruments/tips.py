"""Treasury Inflation-Protected Security instrument.

The TIPS contract models an inflation-linked Treasury with a par floor on the
final principal repayment and explicit index-ratio plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING
from typing import ClassVar

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.errors import InvalidBondSpec
from fuggers_py._core.stub_rules import StubPeriodRules
from fuggers_py._core.types import CashFlow, CashFlowSchedule, Currency, Date, Frequency
from fuggers_py._core.yield_convention import AccruedConvention
from fuggers_py._products.instruments import KindedInstrumentMixin

from ..cashflows import AccruedInterestCalculator, AccruedInterestInputs, Schedule, ScheduleConfig
from ..traits import Bond, BondAnalytics, BondCashFlow, CashFlowType
from fuggers_py._core import YieldCalculationRules
from fuggers_py._reference.bonds.types import BondIdentifiers, InflationIndexType
from .fixed import _reference_period_bounds, _to_decimal

if TYPE_CHECKING:
    from fuggers_py.inflation import InflationConvention, InflationIndexDefinition


InflationFixingSourceLike = object


def _inflation_index_type(convention: InflationConvention) -> InflationIndexType:
    try:
        return InflationIndexType[convention.family]
    except KeyError:
        return InflationIndexType.OTHER


@dataclass(frozen=True, slots=True)
class TipsBond(KindedInstrumentMixin, BondAnalytics, Bond):
    """Inflation-linked US Treasury security with explicit index-ratio plumbing.

    Parameters
    ----------
    _issue_date, _dated_date, _maturity_date:
        Bond issue, dated, and maturity dates.
    _coupon_rate:
        Fixed coupon rate as a raw decimal.
    _inflation_convention:
        Inflation convention used to resolve reference CPI values.
    _base_reference_date:
        Reference date used for the base CPI ratio.
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
    _default_fixing_source:
        Optional default inflation fixing source.
    instrument_id:
        Optional stable instrument identifier.
    """

    KIND: ClassVar[str] = "bond.tips"

    _issue_date: Date
    _dated_date: Date
    _maturity_date: Date
    _coupon_rate: Decimal
    _inflation_convention: InflationConvention
    _base_reference_date: Date
    _frequency: Frequency = Frequency.SEMI_ANNUAL
    _currency: Currency = Currency.USD
    _notional: Decimal = Decimal(100)
    _identifiers: BondIdentifiers = field(default_factory=BondIdentifiers)
    _rules: YieldCalculationRules = field(default_factory=YieldCalculationRules.us_treasury)
    _stub_rules: StubPeriodRules | None = None
    _default_fixing_source: InflationFixingSourceLike | None = None
    instrument_id: InstrumentId | None = None

    _schedule: Schedule = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_coupon_rate", _to_decimal(self._coupon_rate, field_name="coupon_rate"))
        object.__setattr__(self, "_notional", _to_decimal(self._notional, field_name="notional"))
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))

        if self._maturity_date <= self._issue_date:
            raise InvalidBondSpec(reason="maturity_date must be after issue_date.")
        if self._maturity_date <= self._dated_date:
            raise InvalidBondSpec(reason="maturity_date must be after dated_date.")
        if self._dated_date > self._issue_date:
            raise InvalidBondSpec(reason="dated_date must be on or before issue_date.")
        if self._frequency.is_zero():
            raise InvalidBondSpec(reason="TipsBond requires a non-zero coupon frequency.")
        if self._notional <= 0:
            raise InvalidBondSpec(reason="notional must be positive.")
        if self._coupon_rate < Decimal(0) or self._coupon_rate > Decimal("1"):
            raise InvalidBondSpec(reason="coupon_rate must be a non-negative decimal rate between 0 and 1.")
        if self._inflation_convention.currency is not self._currency:
            raise InvalidBondSpec(reason="TipsBond currency must match inflation_convention.currency.")
        if self._base_reference_date > self._maturity_date:
            raise InvalidBondSpec(reason="base_reference_date must be on or before maturity_date.")

        rules = self.rules()
        if rules.frequency != self._frequency:
            raise InvalidBondSpec(
                reason="Bond frequency must match rules.frequency (set via YieldCalculationRules)."
            )

        stub_rules = self._stub_rules or rules.stub_rules
        schedule_config = ScheduleConfig(
            start_date=self._dated_date,
            end_date=self._maturity_date,
            frequency=self._frequency,
            calendar=rules.calendar,
            business_day_convention=rules.business_day_convention,
            end_of_month=rules.end_of_month,
            stub_rules=stub_rules,
        )
        object.__setattr__(self, "_schedule", Schedule.generate(schedule_config))

    @classmethod
    def new(
        cls,
        *,
        issue_date: Date,
        maturity_date: Date,
        coupon_rate: Decimal,
        inflation_convention: InflationIndexDefinition,
        dated_date: Date | None = None,
        base_reference_date: Date | None = None,
        frequency: Frequency = Frequency.SEMI_ANNUAL,
        currency: Currency = Currency.USD,
        notional: Decimal = Decimal(100),
        identifiers: BondIdentifiers | None = None,
        rules: YieldCalculationRules | None = None,
        stub_rules: StubPeriodRules | None = None,
        fixing_source: InflationFixingSourceLike | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> "TipsBond":
        resolved_dated_date = issue_date if dated_date is None else dated_date
        return cls(
            _issue_date=issue_date,
            _dated_date=resolved_dated_date,
            _maturity_date=maturity_date,
            _coupon_rate=coupon_rate,
            _inflation_convention=inflation_convention,
            _base_reference_date=resolved_dated_date if base_reference_date is None else base_reference_date,
            _frequency=frequency,
            _currency=currency,
            _notional=notional,
            _identifiers=identifiers or BondIdentifiers(),
            _rules=rules or YieldCalculationRules.us_treasury(),
            _stub_rules=stub_rules,
            _default_fixing_source=fixing_source,
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

    def dated_date(self) -> Date:
        return self._dated_date

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

    def inflation_convention(self) -> InflationConvention:
        return self._inflation_convention

    def inflation_index_definition(self) -> InflationIndexDefinition:
        return self._inflation_convention

    def inflation_index_type(self) -> InflationIndexType:
        return _inflation_index_type(self._inflation_convention)

    def base_reference_date(self) -> Date:
        return self._base_reference_date

    def reference_cpi(
        self,
        settlement_date: Date,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
    ) -> Decimal:
        """Return the reference CPI for ``settlement_date``."""

        from fuggers_py.inflation import reference_cpi as resolve_reference_cpi

        return resolve_reference_cpi(
            settlement_date,
            self._inflation_convention,
            self._resolve_fixing_source(fixing_source),
        )

    def index_ratio(
        self,
        settlement_date: Date,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
        base_date: Date | None = None,
    ) -> Decimal:
        """Return the reference-index ratio relative to ``base_date``."""

        from fuggers_py.inflation import reference_index_ratio as resolve_reference_index_ratio

        return resolve_reference_index_ratio(
            settlement_date,
            self._base_reference_date if base_date is None else base_date,
            self._inflation_convention,
            self._resolve_fixing_source(fixing_source),
        )

    def adjusted_principal(
        self,
        settlement_date: Date,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
        base_date: Date | None = None,
    ) -> Decimal:
        """Return the inflation-adjusted principal without a maturity floor."""

        return self._notional * self.index_ratio(
            settlement_date,
            fixing_source=fixing_source,
            base_date=base_date,
        )

    def final_principal_redemption(
        self,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
        base_date: Date | None = None,
    ) -> Decimal:
        """Return the maturity principal amount with the TIPS par floor."""

        adjusted_principal = self.adjusted_principal(
            self._schedule.dates[-1],
            fixing_source=fixing_source,
            base_date=base_date,
        )
        return max(adjusted_principal, self._notional)

    def projected_coupon_cash_flows(
        self,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
        settlement_date: Date | None = None,
        base_date: Date | None = None,
    ) -> list[BondCashFlow]:
        """Return coupon cash flows tagged as inflation-linked."""

        resolved_source = self._resolve_fixing_source(fixing_source)
        day_count = self.rules().accrual_day_count_obj()
        flows: list[BondCashFlow] = []

        for index in range(1, len(self._schedule.unadjusted_dates)):
            accrual_start = self._schedule.unadjusted_dates[index - 1]
            accrual_end = self._schedule.unadjusted_dates[index]
            pay_date = self._schedule.dates[index]
            if settlement_date is not None and pay_date <= settlement_date:
                continue

            accrual_factor = day_count.year_fraction(accrual_start, accrual_end)
            base_coupon_amount = self._notional * self._coupon_rate * accrual_factor
            ratio = self.index_ratio(pay_date, fixing_source=resolved_source, base_date=base_date)
            flows.append(
                BondCashFlow(
                    date=pay_date,
                    amount=base_coupon_amount,
                    flow_type=CashFlowType.INFLATION_COUPON,
                    accrual_start=accrual_start,
                    accrual_end=accrual_end,
                    factor=ratio,
                )
            )

        return flows

    def projected_cash_flows(
        self,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
        settlement_date: Date | None = None,
        base_date: Date | None = None,
    ) -> list[BondCashFlow]:
        """Return projected coupon and principal cash flows."""

        resolved_source = self._resolve_fixing_source(fixing_source)
        flows = self.projected_coupon_cash_flows(
            fixing_source=resolved_source,
            settlement_date=settlement_date,
            base_date=base_date,
        )
        principal_date = self._schedule.dates[-1]
        if settlement_date is None or principal_date > settlement_date:
            redemption_amount = self.final_principal_redemption(
                fixing_source=resolved_source,
                base_date=base_date,
            )
            flows.append(
                BondCashFlow(
                    date=principal_date,
                    amount=self._notional,
                    flow_type=CashFlowType.INFLATION_PRINCIPAL,
                    factor=redemption_amount / self._notional,
                )
            )
        flows.sort(key=lambda flow: flow.date)
        return flows

    def cash_flow_schedule(
        self,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
        settlement_date: Date | None = None,
        base_date: Date | None = None,
    ) -> CashFlowSchedule:
        """Return a core cash-flow schedule using inflation cash-flow helpers."""

        schedule = CashFlowSchedule.new()
        for flow in self.projected_cash_flows(
            fixing_source=fixing_source,
            settlement_date=settlement_date,
            base_date=base_date,
        ):
            if flow.flow_type is CashFlowType.INFLATION_COUPON:
                coupon = CashFlow.inflation_coupon(flow.date, flow.factored_amount())
                if flow.accrual_start is not None and flow.accrual_end is not None:
                    coupon = coupon.with_accrual(flow.accrual_start, flow.accrual_end)
                schedule.push(coupon)
            else:
                schedule.push(
                    CashFlow.inflation_principal(flow.date, flow.factored_amount()).with_notional_after(Decimal(0))
                )
        schedule.sort_by_date()
        return schedule

    def cash_flows(
        self,
        from_date: Date | None = None,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
    ) -> list[BondCashFlow]:
        """Return projected cash flows using the attached default fixing source."""

        return self.projected_cash_flows(
            fixing_source=self._resolve_fixing_source(fixing_source),
            settlement_date=from_date,
        )

    def accrued_interest(
        self,
        settlement_date: Date,
        *,
        fixing_source: InflationFixingSourceLike | None = None,
    ) -> Decimal:
        """Return accrued interest on settlement-date adjusted principal."""

        if settlement_date >= self._maturity_date:
            return Decimal(0)

        day_count = self.rules().accrual_day_count_obj()
        resolved_source = self._resolve_fixing_source(fixing_source)
        for index in range(1, len(self._schedule.unadjusted_dates)):
            accrual_start = self._schedule.unadjusted_dates[index - 1]
            accrual_end = self._schedule.unadjusted_dates[index]
            if not (accrual_start < settlement_date < accrual_end):
                continue

            adjusted_principal = self.adjusted_principal(settlement_date, fixing_source=resolved_source)
            accrued_amount = adjusted_principal * self._coupon_rate * day_count.year_fraction(accrual_start, settlement_date)
            if self.rules().accrued_convention is AccruedConvention.EX_DIVIDEND:
                coupon_date = self._schedule.dates[index]
                period_start, period_end = _reference_period_bounds(self._schedule, index)
                inputs = AccruedInterestInputs(
                    settlement_date=settlement_date,
                    accrual_start=accrual_start,
                    accrual_end=accrual_end,
                    coupon_amount=accrued_amount,
                    coupon_date=coupon_date,
                    full_coupon_amount=accrued_amount,
                    period_start=period_start,
                    period_end=period_end,
                )
                return AccruedInterestCalculator.ex_dividend(inputs, rules=self.rules())
            return accrued_amount

        return Decimal(0)

    def _resolve_fixing_source(self, fixing_source: InflationFixingSourceLike | None) -> InflationFixingSourceLike:
        resolved = self._default_fixing_source if fixing_source is None else fixing_source
        if resolved is None:
            raise InvalidBondSpec(
                reason="TipsBond requires an inflation fixing source. Supply one explicitly or bind fixing_source at construction."
            )
        return resolved


__all__ = ["TipsBond"]
