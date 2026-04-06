"""Yield calculation rules (`fuggers_py.reference.bonds.types.yield_rules`)."""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.calendars import BusinessDayConvention
from fuggers_py.core.daycounts import ActActIcma, DayCount, DayCountConvention
from fuggers_py.core.types import Frequency

from ..errors import InvalidBondSpec
from .compounding import CompoundingMethod
from .ex_dividend import ExDividendRules
from .identifiers import CalendarId
from .settlement_rules import SettlementRules
from .stub_rules import StubPeriodRules
from .yield_convention import AccruedConvention, RoundingConvention, YieldConvention


def _day_count(convention: DayCountConvention, *, frequency: Frequency) -> DayCount:
    # `ACT/ACT ICMA` depends on coupon frequency; core's enum maps to semi-annual
    # by default, so we construct the correct instance here.
    if convention is DayCountConvention.ACT_ACT_ICMA:
        if frequency.is_zero():
            raise InvalidBondSpec(reason="ACT/ACT ICMA requires a non-zero frequency.")
        return ActActIcma.new(frequency)
    return convention.to_day_count()


@dataclass(frozen=True, slots=True)
class YieldCalculationRules:
    """Market convention bundle for bond pricing and accrued interest.

    The day-count fields govern accrual, yield solving, and discounting. Raw
    coupon, yield, and spread values remain decimals unless wrapped in a higher
    level quote type.
    """

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
        """Return the default US Treasury convention bundle."""
        return cls.us_treasury()

    @classmethod
    def us_treasury(cls) -> "YieldCalculationRules":
        """Return the standard US Treasury pricing convention."""
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
        """Return the standard US corporate pricing convention."""
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
        """Return the standard UK gilt pricing convention."""
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
        """Return the standard Eurobond pricing convention."""
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
        """Return the standard German Bund pricing convention."""
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
        """Return the standard Japanese JGB pricing convention."""
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
        """Return the day-count object used for coupon accrual."""
        return _day_count(self.accrual_day_count, frequency=self.frequency)

    def yield_day_count_obj(self) -> DayCount:
        """Return the day-count object used for yield solving."""
        return _day_count(self.yield_day_count, frequency=self.frequency)

    def discount_day_count_obj(self) -> DayCount:
        """Return the day-count object used for discounting."""
        return _day_count(self.discount_day_count, frequency=self.frequency)


__all__ = ["YieldCalculationRules"]
