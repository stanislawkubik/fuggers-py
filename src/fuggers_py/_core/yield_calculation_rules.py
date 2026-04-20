"""Shared yield calculation rule bundle."""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py._core.calendars import BusinessDayConvention
from fuggers_py._core.daycounts import ActActIcma, DayCount, DayCountConvention
from fuggers_py._core.types import Frequency

from .calendar_id import CalendarId
from .compounding import CompoundingMethod
from .errors import InvalidBondSpec
from .ex_dividend import ExDividendRules
from .settlement_rules import SettlementRules
from .stub_rules import StubPeriodRules
from .yield_convention import AccruedConvention, RoundingConvention, YieldConvention


def _day_count(convention: DayCountConvention, *, frequency: Frequency) -> DayCount:
    if convention is DayCountConvention.ACT_ACT_ICMA:
        if frequency.is_zero():
            raise InvalidBondSpec(reason="ACT/ACT ICMA requires a non-zero frequency.")
        return ActActIcma.new(frequency)
    return convention.to_day_count()


@dataclass(frozen=True, slots=True)
class YieldCalculationRules:
    """Market convention bundle for bond pricing and accrued interest."""

    convention: YieldConvention
    compounding: CompoundingMethod
    frequency: Frequency
    calendar: CalendarId
    business_day_convention: BusinessDayConvention
    end_of_month: bool
    settlement_rules: SettlementRules
    stub_rules: StubPeriodRules
    ex_dividend_rules: ExDividendRules | None
    accrued_convention: AccruedConvention
    accrual_day_count: DayCountConvention
    yield_day_count: DayCountConvention
    discount_day_count: DayCountConvention
    rounding: RoundingConvention | None
    description: str

    @classmethod
    def default(cls) -> "YieldCalculationRules":
        return cls.us_treasury()

    @classmethod
    def us_treasury(cls) -> "YieldCalculationRules":
        return cls(
            convention=YieldConvention.STREET_CONVENTION,
            compounding=CompoundingMethod.periodic(2),
            frequency=Frequency.SEMI_ANNUAL,
            calendar=CalendarId.us_government(),
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            end_of_month=True,
            settlement_rules=SettlementRules.us_treasury(),
            stub_rules=StubPeriodRules.default(),
            ex_dividend_rules=None,
            accrued_convention=AccruedConvention.STANDARD,
            accrual_day_count=DayCountConvention.ACT_ACT_ICMA,
            yield_day_count=DayCountConvention.ACT_ACT_ICMA,
            discount_day_count=DayCountConvention.ACT_ACT_ICMA,
            rounding=None,
            description="US Treasury Street Convention",
        )

    @classmethod
    def us_corporate(cls) -> "YieldCalculationRules":
        return cls(
            convention=YieldConvention.STREET_CONVENTION,
            compounding=CompoundingMethod.periodic(2),
            frequency=Frequency.SEMI_ANNUAL,
            calendar=CalendarId.sifma(),
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            end_of_month=True,
            settlement_rules=SettlementRules.us_corporate(),
            stub_rules=StubPeriodRules.default(),
            ex_dividend_rules=None,
            accrued_convention=AccruedConvention.STANDARD,
            accrual_day_count=DayCountConvention.THIRTY_360_US,
            yield_day_count=DayCountConvention.THIRTY_360_US,
            discount_day_count=DayCountConvention.THIRTY_360_US,
            rounding=None,
            description="US Corporate Bond Convention",
        )

    @classmethod
    def uk_gilt(cls) -> "YieldCalculationRules":
        return cls(
            convention=YieldConvention.ISMA,
            compounding=CompoundingMethod.actual_period(2),
            frequency=Frequency.SEMI_ANNUAL,
            calendar=CalendarId.uk(),
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            end_of_month=True,
            settlement_rules=SettlementRules.uk_gilt(),
            stub_rules=StubPeriodRules.default(),
            ex_dividend_rules=ExDividendRules.uk_gilt(),
            accrued_convention=AccruedConvention.EX_DIVIDEND,
            accrual_day_count=DayCountConvention.ACT_ACT_ICMA,
            yield_day_count=DayCountConvention.ACT_ACT_ICMA,
            discount_day_count=DayCountConvention.ACT_ACT_ICMA,
            rounding=None,
            description="UK Gilt ISMA Convention",
        )

    @classmethod
    def eurobond(cls) -> "YieldCalculationRules":
        return cls(
            convention=YieldConvention.ISMA,
            compounding=CompoundingMethod.periodic(1),
            frequency=Frequency.ANNUAL,
            calendar=CalendarId.target2(),
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            end_of_month=True,
            settlement_rules=SettlementRules.eurobond(),
            stub_rules=StubPeriodRules.default(),
            ex_dividend_rules=None,
            accrued_convention=AccruedConvention.STANDARD,
            accrual_day_count=DayCountConvention.THIRTY_360_E,
            yield_day_count=DayCountConvention.THIRTY_360_E,
            discount_day_count=DayCountConvention.THIRTY_360_E,
            rounding=None,
            description="Eurobond Convention",
        )

    @classmethod
    def german_bund(cls) -> "YieldCalculationRules":
        return cls(
            convention=YieldConvention.STREET_CONVENTION,
            compounding=CompoundingMethod.periodic(1),
            frequency=Frequency.ANNUAL,
            calendar=CalendarId.target2(),
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            end_of_month=True,
            settlement_rules=SettlementRules.german_bund(),
            stub_rules=StubPeriodRules.default(),
            ex_dividend_rules=None,
            accrued_convention=AccruedConvention.STANDARD,
            accrual_day_count=DayCountConvention.ACT_ACT_ICMA,
            yield_day_count=DayCountConvention.ACT_ACT_ICMA,
            discount_day_count=DayCountConvention.ACT_ACT_ICMA,
            rounding=None,
            description="German Bund Convention",
        )

    @classmethod
    def japanese_jgb(cls) -> "YieldCalculationRules":
        return cls(
            convention=YieldConvention.STREET_CONVENTION,
            compounding=CompoundingMethod.periodic(2),
            frequency=Frequency.SEMI_ANNUAL,
            calendar=CalendarId.japan(),
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            end_of_month=True,
            settlement_rules=SettlementRules(days=2),
            stub_rules=StubPeriodRules.default(),
            ex_dividend_rules=None,
            accrued_convention=AccruedConvention.STANDARD,
            accrual_day_count=DayCountConvention.ACT_ACT_ICMA,
            yield_day_count=DayCountConvention.ACT_ACT_ICMA,
            discount_day_count=DayCountConvention.ACT_ACT_ICMA,
            rounding=None,
            description="Japanese JGB Convention",
        )

    def accrual_day_count_obj(self) -> DayCount:
        return _day_count(self.accrual_day_count, frequency=self.frequency)

    def yield_day_count_obj(self) -> DayCount:
        return _day_count(self.yield_day_count, frequency=self.frequency)

    def discount_day_count_obj(self) -> DayCount:
        return _day_count(self.discount_day_count, frequency=self.frequency)


__all__ = ["YieldCalculationRules"]
