"""Zero-coupon inflation swaps.

The fixed leg and inflation leg settle only once at maturity. The fixed-leg
direction follows the usual pay/receive convention and the inflation leg takes
the opposite side.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from fuggers_py.reference.bonds.types import CalendarId
from fuggers_py.core.calendars import BusinessDayConvention
from fuggers_py.core.types import Currency, Date
from fuggers_py.core.ids import InstrumentId
from fuggers_py.products.instruments import KindedInstrumentMixin
from fuggers_py.reference.inflation import (
    InflationConvention,
    InflationIndexDefinition,
    USD_CPI_U_NSA,
)

from .common import PayReceive


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class ZeroCouponInflationSwap(KindedInstrumentMixin):
    """Single-payment zero-coupon inflation swap.

    ``pay_receive`` is the direction of the fixed leg. The inflation leg is the
    opposite direction and pays the realized inflation ratio minus one at
    maturity.

    Parameters
    ----------
    trade_date, maturity_date:
        Trade date and final payment date anchor.
    notional:
        Trade notional in currency units.
    fixed_rate:
        Fixed rate as a raw decimal.
    pay_receive:
        Direction of the fixed leg.
    inflation_convention:
        Inflation index family and lag convention used for settlement.
    effective_date:
        Optional effective date; if omitted, it is derived from the payment
        calendar and standard settlement lag.
    currency:
        Contract currency.
    payment_calendar:
        Calendar used to adjust the final payment date.
    business_day_convention:
        Business-day rule used on the payment date.
    instrument_id:
        Optional stable identifier for the swap.
    """

    KIND: ClassVar[str] = "rates.swap.inflation.zero_coupon"

    trade_date: Date
    maturity_date: Date
    notional: Decimal
    fixed_rate: Decimal
    pay_receive: PayReceive | str = PayReceive.PAY
    inflation_convention: InflationConvention = USD_CPI_U_NSA
    effective_date: Date | None = None
    currency: Currency | str = Currency.USD
    payment_calendar: CalendarId | str = CalendarId.sifma()
    business_day_convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "fixed_rate", _to_decimal(self.fixed_rate))
        object.__setattr__(self, "pay_receive", PayReceive.parse(self.pay_receive))
        if not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        if not isinstance(self.payment_calendar, CalendarId):
            object.__setattr__(self, "payment_calendar", CalendarId.new(str(self.payment_calendar)))
        if not isinstance(self.business_day_convention, BusinessDayConvention):
            normalized = str(self.business_day_convention).strip().upper().replace("-", "_").replace(" ", "_")
            object.__setattr__(self, "business_day_convention", BusinessDayConvention[normalized])
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.effective_date is None:
            calendar = self.payment_calendar.to_calendar()
            object.__setattr__(self, "effective_date", calendar.settlement_date(self.trade_date, 2))
        if self.inflation_convention is None:
            raise ValueError("ZeroCouponInflationSwap requires an inflation_convention.")
        if self.maturity_date <= self.effective_date:
            raise ValueError("ZeroCouponInflationSwap requires maturity_date after effective_date.")
        if self.notional <= Decimal(0):
            raise ValueError("ZeroCouponInflationSwap notional must be positive.")
        if self.currency is not self.inflation_convention.currency:
            raise ValueError("ZeroCouponInflationSwap currency must match inflation_convention.currency.")

    @classmethod
    def new(
        cls,
        *,
        trade_date: Date,
        maturity_date: Date,
        notional: Decimal,
        fixed_rate: Decimal,
        pay_receive: PayReceive | str = PayReceive.PAY,
        inflation_convention: InflationIndexDefinition = USD_CPI_U_NSA,
        effective_date: Date | None = None,
        currency: Currency | str = Currency.USD,
        payment_calendar: CalendarId | str = CalendarId.sifma(),
        business_day_convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING,
        instrument_id: InstrumentId | None = None,
    ) -> "ZeroCouponInflationSwap":
        """Construct a zero-coupon inflation swap."""

        return cls(
            trade_date=trade_date,
            effective_date=effective_date,
            maturity_date=maturity_date,
            notional=notional,
            fixed_rate=fixed_rate,
            pay_receive=pay_receive,
            currency=currency,
            inflation_convention=inflation_convention,
            payment_calendar=payment_calendar,
            business_day_convention=business_day_convention,
            instrument_id=instrument_id,
        )

    def payment_date(self) -> Date:
        """Return the maturity payment date after business-day adjustment."""

        return self.payment_calendar.to_calendar().adjust(self.maturity_date, self.business_day_convention)

    def fixed_leg_sign(self) -> Decimal:
        """Return the fixed-leg cash-flow sign."""

        return self.pay_receive.sign()

    def inflation_leg_sign(self) -> Decimal:
        """Return the inflation-leg cash-flow sign."""

        return self.pay_receive.opposite().sign()

    def fixed_leg_year_fraction(self) -> Decimal:
        """Return the fixed-leg day-count fraction.

        The first-release USD market convention is a single 1/1 accrual.
        """

        return Decimal(1)

    def index_initial_date(self) -> Date:
        """Return the floating leg start date used for the initial reference CPI."""

        return self.effective_date

    def index_final_date(self) -> Date:
        """Return the floating leg end date used for the final reference CPI."""

        return self.maturity_date


__all__ = ["ZeroCouponInflationSwap"]
