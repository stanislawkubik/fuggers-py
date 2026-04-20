"""Shared settlement adjustment and settlement rule types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fuggers_py._core.calendars import BusinessDayConvention, Calendar
from fuggers_py._core.types import Date

from .errors import SettlementError


class SettlementAdjustment(str, Enum):
    """Business-day adjustment applied after adding settlement lag."""

    NONE = "NONE"
    FOLLOWING = "FOLLOWING"
    MODIFIED_FOLLOWING = "MODIFIED_FOLLOWING"
    PRECEDING = "PRECEDING"
    MODIFIED_PRECEDING = "MODIFIED_PRECEDING"

    def to_business_day_convention(self) -> BusinessDayConvention | None:
        return {
            SettlementAdjustment.NONE: None,
            SettlementAdjustment.FOLLOWING: BusinessDayConvention.FOLLOWING,
            SettlementAdjustment.MODIFIED_FOLLOWING: BusinessDayConvention.MODIFIED_FOLLOWING,
            SettlementAdjustment.PRECEDING: BusinessDayConvention.PRECEDING,
            SettlementAdjustment.MODIFIED_PRECEDING: BusinessDayConvention.MODIFIED_PRECEDING,
        }[self]


@dataclass(frozen=True, slots=True)
class SettlementRules:
    """Settlement lag and adjustment convention for a bond market."""

    days: int
    use_business_days: bool = True
    adjustment: SettlementAdjustment = SettlementAdjustment.MODIFIED_FOLLOWING
    allow_same_day: bool = True

    @classmethod
    def us_treasury(cls) -> "SettlementRules":
        return cls(days=1, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    @classmethod
    def us_corporate(cls) -> "SettlementRules":
        return cls(days=2, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    @classmethod
    def uk_gilt(cls) -> "SettlementRules":
        return cls(days=1, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    @classmethod
    def german_bund(cls) -> "SettlementRules":
        return cls(days=2, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    @classmethod
    def eurobond(cls) -> "SettlementRules":
        return cls(days=2, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    def settlement_date(self, trade_date: Date, calendar: Calendar) -> Date:
        if self.days == 0 and not self.allow_same_day:
            raise SettlementError(reason="Same-day settlement not allowed by rules.")

        base = (
            calendar.add_business_days(trade_date, self.days)
            if self.use_business_days
            else trade_date.add_days(self.days)
        )
        bdc = self.adjustment.to_business_day_convention()
        return base if bdc is None else calendar.adjust(base, bdc)


__all__ = ["SettlementAdjustment", "SettlementRules"]
