"""Government bond curve instruments.

These helpers expose lightweight government instruments intended for
curve calibration workflows. Quotes are interpreted as clean prices in
percent-of-par unless explicitly converted otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.products.bonds.cashflows import Schedule, ScheduleConfig
from fuggers_py.reference.bonds.types import CalendarId, PriceQuote, StubPeriodRules
from fuggers_py.core.calendars import BusinessDayConvention
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Currency, Date, Frequency


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _price_to_percentage(price: PriceQuote | Decimal | object) -> Decimal:
    if isinstance(price, PriceQuote):
        return price.as_percentage()
    return _to_decimal(price)


@dataclass(frozen=True, slots=True)
class GovernmentZeroCoupon:
    """Zero-coupon government instrument used in calibration workflows.

    Notes
    -----
    Input and output prices are quoted as clean prices in percent-of-par.
    """

    maturity: Date
    currency: Currency = Currency.USD
    notional: Decimal = Decimal(100)
    day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED

    def calibration_target_from_price(self, price: PriceQuote | Decimal | object) -> Decimal:
        """Convert a clean price quote into a discount-factor target."""

        pct = _price_to_percentage(price)
        return pct / Decimal(100)

    def repriced_discount_factor(self, curve: YieldCurve, *, settlement_date: Date | None = None) -> Decimal:
        """Return the discount factor from settlement to maturity implied by ``curve``."""

        settle = settlement_date or curve.reference_date()
        df_settle = curve.discount_factor(settle)
        df = curve.discount_factor(self.maturity)
        if df_settle == 0:
            return Decimal(0)
        return df / df_settle

    def repriced_quote(self, curve: YieldCurve, *, settlement_date: Date | None = None) -> Decimal:
        """Return the clean price implied by the curve (percent-of-par)."""

        df = self.repriced_discount_factor(curve, settlement_date=settlement_date)
        return df * Decimal(100)


@dataclass(frozen=True, slots=True)
class GovernmentCouponBond:
    """Coupon-paying government bond used as a curve calibration instrument.

    Notes
    -----
    Quotes are treated as clean prices in percent-of-par. The repricing helper
    returns a synthetic clean price and intentionally ignores accrued interest.
    """

    maturity: Date
    coupon_rate: Decimal
    frequency: Frequency
    currency: Currency = Currency.USD
    notional: Decimal = Decimal(100)
    day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    calendar: CalendarId = CalendarId.weekend_only()
    business_day_convention: BusinessDayConvention = BusinessDayConvention.MODIFIED_FOLLOWING
    end_of_month: bool = True
    stub_rules: StubPeriodRules = StubPeriodRules.default()

    def calibration_target_from_price(self, price: PriceQuote | Decimal | object) -> Decimal:
        """Normalize a clean price quote to percentage-of-par."""

        return _price_to_percentage(price)

    def _schedule(self, reference_date: Date) -> Schedule:
        config = ScheduleConfig(
            start_date=reference_date,
            end_date=self.maturity,
            frequency=self.frequency,
            calendar=self.calendar,
            business_day_convention=self.business_day_convention,
            end_of_month=self.end_of_month,
            stub_rules=self.stub_rules,
        )
        return Schedule.generate(config)

    def price_from_curve(self, curve: YieldCurve, *, settlement_date: Date | None = None) -> Decimal:
        """Compute a clean price (percent-of-par) from a discount curve.

        Assumes settlement at the curve reference date unless overridden and
        ignores accrued interest (synthetic par-style pricing).
        """

        settle = settlement_date or curve.reference_date()
        schedule = self._schedule(settle)
        day_count = self.day_count.to_day_count()

        df_settle = curve.discount_factor(settle)
        if df_settle == 0:
            return Decimal(0)

        pv = Decimal(0)
        for i in range(1, len(schedule.unadjusted_dates)):
            accrual_start = schedule.unadjusted_dates[i - 1]
            accrual_end = schedule.unadjusted_dates[i]
            tau = day_count.year_fraction(accrual_start, accrual_end)
            coupon = self.notional * self.coupon_rate * tau
            principal = self.notional if i == len(schedule.unadjusted_dates) - 1 else Decimal(0)
            amount = coupon + principal
            df = curve.discount_factor(schedule.dates[i]) / df_settle
            pv += amount * df

        return (pv / self.notional) * Decimal(100)

    def repriced_quote(self, curve: YieldCurve, *, settlement_date: Date | None = None) -> Decimal:
        """Return the synthetic clean price implied by ``curve``."""

        return self.price_from_curve(curve, settlement_date=settlement_date)


__all__ = ["GovernmentZeroCoupon", "GovernmentCouponBond"]
