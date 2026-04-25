"""Funding-domain product definitions owned by :mod:`fuggers_py.funding`."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias, overload

from fuggers_py._core import Currency, Date, DayCount, DayCountConvention, InstrumentId

DecimalInput: TypeAlias = Decimal | int | float | str


@overload
def _to_decimal(value: None) -> None: ...


@overload
def _to_decimal(value: DecimalInput) -> Decimal: ...


def _to_decimal(value: DecimalInput | None) -> Decimal | None:
    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_day_count(value: DayCountConvention | str) -> DayCountConvention:
    if isinstance(value, DayCountConvention):
        return value
    normalized = value.strip().upper().replace("/", "_")
    aliases = {
        "ACT360": DayCountConvention.ACT_360,
        "ACT_360": DayCountConvention.ACT_360,
        "ACT365F": DayCountConvention.ACT_365_FIXED,
        "ACT_365_FIXED": DayCountConvention.ACT_365_FIXED,
        "ACT365L": DayCountConvention.ACT_365_LEAP,
        "ACT_365_LEAP": DayCountConvention.ACT_365_LEAP,
        "30E_360": DayCountConvention.THIRTY_360_E,
        "30_360_E": DayCountConvention.THIRTY_360_E,
        "30_360_US": DayCountConvention.THIRTY_360_US,
    }
    if normalized in aliases:
        return aliases[normalized]
    return DayCountConvention[normalized]


@dataclass(frozen=True, slots=True, init=False)
class RepoTrade:
    """Repurchase agreement trade expressed in cash and collateral terms."""

    start_date: Date
    end_date: Date
    rate: Decimal
    collateral_price: Decimal
    haircut: Decimal = Decimal(0)
    notional: Decimal | None = None
    cash_amount: Decimal | None = None
    currency: Currency = Currency.USD
    day_count_convention: DayCountConvention = DayCountConvention.ACT_360
    collateral_instrument_id: InstrumentId | None = None

    def __init__(
        self,
        start_date: Date,
        end_date: Date,
        rate: DecimalInput,
        collateral_price: DecimalInput,
        haircut: DecimalInput = Decimal(0),
        notional: DecimalInput | None = None,
        cash_amount: DecimalInput | None = None,
        currency: Currency | str = Currency.USD,
        day_count_convention: DayCountConvention | str = DayCountConvention.ACT_360,
        collateral_instrument_id: InstrumentId | str | None = None,
    ) -> None:
        rate_value = _to_decimal(rate)
        collateral_price_value = _to_decimal(collateral_price)
        haircut_value = _to_decimal(haircut)
        notional_value = _to_decimal(notional)
        cash_amount_value = _to_decimal(cash_amount)
        currency_value = currency if isinstance(currency, Currency) else Currency.from_code(str(currency))
        day_count_convention_value = _coerce_day_count(day_count_convention)
        collateral_instrument_id_value = None if collateral_instrument_id is None else InstrumentId.parse(collateral_instrument_id)

        object.__setattr__(self, "start_date", start_date)
        object.__setattr__(self, "end_date", end_date)
        object.__setattr__(self, "rate", rate_value)
        object.__setattr__(self, "collateral_price", collateral_price_value)
        object.__setattr__(self, "haircut", haircut_value)
        object.__setattr__(self, "notional", notional_value)
        object.__setattr__(self, "cash_amount", cash_amount_value)
        object.__setattr__(self, "currency", currency_value)
        object.__setattr__(self, "day_count_convention", day_count_convention_value)
        object.__setattr__(self, "collateral_instrument_id", collateral_instrument_id_value)

        if end_date <= start_date:
            raise ValueError("RepoTrade requires end_date after start_date.")
        if haircut_value < Decimal(0) or haircut_value >= Decimal(1):
            raise ValueError("haircut must lie in [0, 1).")
        if notional_value is None and cash_amount_value is None:
            raise ValueError("RepoTrade requires either notional or cash_amount.")
        if notional_value is not None and notional_value <= Decimal(0):
            raise ValueError("notional must be positive when provided.")
        if cash_amount_value is not None and cash_amount_value <= Decimal(0):
            raise ValueError("cash_amount must be positive when provided.")

    def day_count(self) -> DayCount:
        return self.day_count_convention.to_day_count()

    def year_fraction(self) -> Decimal:
        return self.day_count().year_fraction(self.start_date, self.end_date)

    def collateral_market_value(self) -> Decimal:
        if self.notional is not None:
            return self.notional * self.collateral_price / Decimal(100)
        cash_amount = self.cash_amount
        if cash_amount is None:
            raise ValueError("RepoTrade requires either notional or cash_amount.")
        return cash_amount / (Decimal(1) - self.haircut)

    def haircut_amount(self) -> Decimal:
        return self.collateral_market_value() * self.haircut

    def cash_lent(self) -> Decimal:
        if self.cash_amount is not None:
            return self.cash_amount
        return self.collateral_market_value() * (Decimal(1) - self.haircut)

    def interest_amount(self) -> Decimal:
        return self.cash_lent() * self.rate * self.year_fraction()

    def repurchase_amount(self) -> Decimal:
        return self.cash_lent() + self.interest_amount()


__all__ = ["RepoTrade"]
