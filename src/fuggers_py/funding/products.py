"""Funding-domain product definitions owned by :mod:`fuggers_py.funding`."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core import Currency, Date, DayCountConvention, InstrumentId


def _to_decimal(value: object | None) -> Decimal | None:
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


@dataclass(frozen=True, slots=True)
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
    day_count_convention: DayCountConvention | str = DayCountConvention.ACT_360
    collateral_instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rate", _to_decimal(self.rate))
        object.__setattr__(self, "collateral_price", _to_decimal(self.collateral_price))
        if self.notional is not None:
            object.__setattr__(self, "notional", _to_decimal(self.notional))
        if self.cash_amount is not None:
            object.__setattr__(self, "cash_amount", _to_decimal(self.cash_amount))
        object.__setattr__(self, "haircut", _to_decimal(self.haircut))
        if not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        object.__setattr__(self, "day_count_convention", _coerce_day_count(self.day_count_convention))
        if self.collateral_instrument_id is not None:
            object.__setattr__(self, "collateral_instrument_id", InstrumentId.parse(self.collateral_instrument_id))
        if self.end_date <= self.start_date:
            raise ValueError("RepoTrade requires end_date after start_date.")
        if self.haircut < Decimal(0) or self.haircut >= Decimal(1):
            raise ValueError("haircut must lie in [0, 1).")
        if self.notional is None and self.cash_amount is None:
            raise ValueError("RepoTrade requires either notional or cash_amount.")
        if self.notional is not None and self.notional <= Decimal(0):
            raise ValueError("notional must be positive when provided.")
        if self.cash_amount is not None and self.cash_amount <= Decimal(0):
            raise ValueError("cash_amount must be positive when provided.")

    def day_count(self):
        return self.day_count_convention.to_day_count()

    def year_fraction(self) -> Decimal:
        return self.day_count().year_fraction(self.start_date, self.end_date)

    def collateral_market_value(self) -> Decimal:
        if self.notional is not None:
            return self.notional * self.collateral_price / Decimal(100)
        return self.cash_amount / (Decimal(1) - self.haircut)

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
