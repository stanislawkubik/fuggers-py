"""Callable and puttable bond instruments.

This module models embedded exercise features on top of a fixed-rate base
bond. Call schedules support European, Bermudan, American, and make-whole
exercise; put schedules model issuer putback rights.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, Iterable

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.types import Currency, Date, Frequency, Price
from fuggers_py.bonds._instrument_base import KindedInstrumentMixin

from ..cashflows.schedule import Schedule
from fuggers_py.bonds.errors import InvalidBondSpec
from ..traits import Bond, BondAnalytics, BondCashFlow, CashFlowType
from fuggers_py.bonds.types import BondIdentifiers, BondType, PutEntry, PutSchedule, PutType
from fuggers_py._core import YieldCalculationRules
from .fixed import FixedBond

if TYPE_CHECKING:
    from fuggers_py.bonds.pricing import BondPricer, StandardYieldEngine


def _to_decimal(value: object, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


class CallType(str, Enum):
    """Exercise style for a call schedule."""

    EUROPEAN = "EUROPEAN"
    AMERICAN = "AMERICAN"
    BERMUDAN = "BERMUDAN"
    MAKE_WHOLE = "MAKE_WHOLE"


@dataclass(frozen=True, slots=True)
class CallEntry:
    """One callable exercise date and redemption price.

    Parameters
    ----------
    call_date:
        Exercise date.
    call_price:
        Redemption price quoted in percent of par.
    call_type:
        Exercise style for the entry.
    call_end_date:
        Optional end date for American-style windows.
    make_whole_spread:
        Optional make-whole spread as a raw decimal.
    """

    call_date: Date
    call_price: Decimal
    call_type: CallType = CallType.EUROPEAN
    call_end_date: Date | None = None
    make_whole_spread: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "call_price", _to_decimal(self.call_price, field_name="call_price"))
        if self.make_whole_spread is not None:
            object.__setattr__(
                self,
                "make_whole_spread",
                _to_decimal(self.make_whole_spread, field_name="make_whole_spread"),
            )
        if self.call_price <= 0:
            raise InvalidBondSpec(reason="call_price must be positive.")
        if self.call_end_date is not None and self.call_end_date < self.call_date:
            raise InvalidBondSpec(reason="call_end_date must be on or after call_date.")

    def is_exercisable_on(self, date: Date, *, next_call_date: Date | None = None) -> bool:
        """Return whether the call may be exercised on ``date``."""
        if self.call_type in {CallType.EUROPEAN, CallType.BERMUDAN, CallType.MAKE_WHOLE}:
            return date == self.call_date
        end_date = self.call_end_date or next_call_date
        if end_date is None:
            return date >= self.call_date
        return self.call_date <= date <= end_date


@dataclass(frozen=True, slots=True)
class CallSchedule:
    """Ordered collection of call exercises with optional protection.

    Parameters
    ----------
    entries:
        Callable exercise entries.
    protection_end_date:
        Optional end date for the call protection window.
    """

    entries: tuple[CallEntry, ...]
    protection_end_date: Date | None = None

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.entries, key=lambda entry: entry.call_date))
        if not ordered:
            raise InvalidBondSpec(reason="CallSchedule requires at least one call entry.")
        for index in range(1, len(ordered)):
            if ordered[index].call_date <= ordered[index - 1].call_date:
                raise InvalidBondSpec(reason="CallSchedule entries must have strictly increasing call dates.")
        object.__setattr__(self, "entries", ordered)

    @classmethod
    def new(
        cls,
        entries: Iterable[CallEntry],
        *,
        protection_end_date: Date | None = None,
    ) -> "CallSchedule":
        """Create a schedule from an iterable of call entries."""
        return cls(entries=tuple(entries), protection_end_date=protection_end_date)

    def is_protected(self, date: Date) -> bool:
        """Return whether ``date`` falls inside the call protection window."""
        return self.protection_end_date is not None and date < self.protection_end_date

    def future_entries(self, settlement_date: Date) -> list[CallEntry]:
        """Return call entries strictly after ``settlement_date``."""
        return [entry for entry in self.entries if entry.call_date > settlement_date]

    def first_call_after(self, settlement_date: Date) -> CallEntry | None:
        """Return the first exercisable call after settlement, if any."""
        for entry in self.entries:
            if entry.call_date > settlement_date and not self.is_protected(entry.call_date):
                return entry
        return None

    def entry_for_date(self, date: Date, *, maturity_date: Date | None = None) -> CallEntry | None:
        """Return the entry exercisable on ``date`` or ``None`` if protected."""
        if self.is_protected(date):
            return None
        for index, entry in enumerate(self.entries):
            next_call_date = self.entries[index + 1].call_date if index + 1 < len(self.entries) else maturity_date
            if entry.is_exercisable_on(date, next_call_date=next_call_date):
                return entry
        return None

    def call_price_on(self, date: Date, *, maturity_date: Date | None = None) -> Decimal | None:
        """Return the call redemption price on ``date`` if exercisable."""
        entry = self.entry_for_date(date, maturity_date=maturity_date)
        return None if entry is None else entry.call_price


@dataclass(frozen=True, slots=True)
class CallableBond(KindedInstrumentMixin, BondAnalytics, Bond):
    """Fixed-rate bond with embedded call and/or put schedules.

    Parameters
    ----------
    base_bond:
        Fixed-rate bond that serves as the base cash-flow stream.
    call_schedule:
        Optional call schedule.
    put_schedule_data:
        Optional put schedule.

    Notes
    -----
    Yield calculations are reported as raw decimal yields. Workout dates are
    the future call, put, and maturity dates that remain after settlement.
    """

    KIND: ClassVar[str] = "bond.callable"

    base_bond: FixedBond
    call_schedule: CallSchedule | None = None
    put_schedule_data: PutSchedule | None = None

    def __post_init__(self) -> None:
        maturity = self.base_bond.maturity_date()
        if self.call_schedule is None and self.put_schedule_data is None:
            raise InvalidBondSpec(reason="CallableBond requires a call or put schedule.")
        if self.call_schedule is not None:
            for call_entry in self.call_schedule.entries:
                if call_entry.call_date <= self.base_bond.issue_date():
                    raise InvalidBondSpec(reason="call dates must be after the issue date.")
                if call_entry.call_date >= maturity:
                    raise InvalidBondSpec(reason="call dates must be before maturity.")
        if self.put_schedule_data is not None:
            for put_entry in self.put_schedule_data.entries:
                if put_entry.put_date <= self.base_bond.issue_date():
                    raise InvalidBondSpec(reason="put dates must be after the issue date.")
                if put_entry.put_date >= maturity:
                    raise InvalidBondSpec(reason="put dates must be before maturity.")

    def identifiers(self) -> BondIdentifiers:
        return self.base_bond.identifiers()

    @property
    def instrument_id(self) -> InstrumentId | None:
        """Return the wrapped base bond identity."""
        return self.base_bond.instrument_id

    def currency(self) -> Currency:
        return self.base_bond.currency()

    def notional(self) -> Decimal:
        return self.base_bond.notional()

    def issue_date(self) -> Date:
        return self.base_bond.issue_date()

    def maturity_date(self) -> Date:
        return self.base_bond.maturity_date()

    def frequency(self) -> Frequency:
        return self.base_bond.frequency()

    def rules(self) -> YieldCalculationRules:
        return self.base_bond.rules()

    def schedule(self) -> Schedule:
        return self.base_bond.schedule()

    def cash_flows(self, from_date: Date | None = None) -> list[BondCashFlow]:
        return self.base_bond.cash_flows(from_date)

    def accrued_interest(self, settlement_date: Date) -> Decimal:
        return self.base_bond.accrued_interest(settlement_date)

    def bond_type(self) -> BondType:
        if self.call_schedule is not None and self.put_schedule_data is not None:
            return BondType.CALLABLE_AND_PUTTABLE
        if self.call_schedule is not None:
            if any(entry.call_type is CallType.MAKE_WHOLE for entry in self.call_schedule.entries):
                return BondType.MAKE_WHOLE_CALLABLE
            return BondType.CALLABLE
        return BondType.PUTTABLE

    def is_callable_on(self, date: Date) -> bool:
        """Return whether the bond is callable on ``date``."""
        if self.call_schedule is None:
            return False
        return self.call_schedule.call_price_on(date, maturity_date=self.maturity_date()) is not None

    def put_schedule(self) -> PutSchedule | None:
        """Return the embedded put schedule, if one exists."""
        return self.put_schedule_data

    def first_call(self, settlement_date: Date) -> CallEntry | None:
        """Return the first future call entry after settlement."""
        if self.call_schedule is None:
            return None
        return self.call_schedule.first_call_after(settlement_date)

    def next_call(self, settlement_date: Date) -> CallEntry | None:
        """Alias for :meth:`first_call`."""
        return self.first_call(settlement_date)

    def first_put(self, settlement_date: Date) -> PutEntry | None:
        """Return the first future put entry after settlement."""
        if self.put_schedule_data is None:
            return None
        return self.put_schedule_data.first_put_after(settlement_date)

    def next_put(self, settlement_date: Date) -> PutEntry | None:
        """Alias for :meth:`first_put`."""
        return self.first_put(settlement_date)

    def is_putable_on(self, date: Date) -> bool:
        """Return whether the bond is putable on ``date``."""
        if self.put_schedule_data is None:
            return False
        return self.put_schedule_data.put_price_on(date, maturity_date=self.maturity_date()) is not None

    def call_price_on(self, date: Date, *, benchmark_yield: Decimal | None = None) -> Decimal | None:
        """Return the call price on ``date``.

        For make-whole calls, ``benchmark_yield`` is the reference yield used to
        discount remaining cash flows at ``benchmark_yield + make_whole_spread``.
        The make-whole value is floored at the contractual call price.
        """
        if self.call_schedule is None:
            return None
        entry = self.call_schedule.entry_for_date(date, maturity_date=self.maturity_date())
        if entry is None:
            return None
        if entry.call_type is not CallType.MAKE_WHOLE or benchmark_yield is None:
            return entry.call_price
        spread = entry.make_whole_spread or Decimal(0)
        discount_rate = float(benchmark_yield + spread)
        remaining = [cf for cf in self.base_bond.cash_flows(date) if cf.date > date]
        if not remaining:
            return entry.call_price
        present_value = 0.0
        for cf in remaining:
            years = max(float(date.days_between(cf.date)) / 365.0, 0.0)
            present_value += float(cf.factored_amount()) / ((1.0 + discount_rate) ** years)
        return max(entry.call_price, Decimal(str(present_value)))

    def cash_flows_to_call(self, call_date: Date) -> list[BondCashFlow]:
        """Return cash flows truncated at the call date and redeemed there."""
        if self.call_schedule is None:
            raise InvalidBondSpec(reason="No call schedule configured for this bond.")
        call_price = self.call_price_on(call_date)
        if call_price is None:
            raise InvalidBondSpec(reason="call_date is not exercisable for this call schedule.")

        flows: list[BondCashFlow] = []
        matched_call_date = False
        for cf in self.base_bond.cash_flows():
            if cf.date < call_date:
                flows.append(cf)
                continue
            if cf.date == call_date:
                coupon_amount = cf.factored_amount()
                if cf.is_principal():
                    coupon_amount -= self.notional()
                flows.append(
                    BondCashFlow(
                        date=cf.date,
                        amount=coupon_amount + call_price,
                        flow_type=CashFlowType.COUPON_AND_PRINCIPAL,
                        accrual_start=cf.accrual_start,
                        accrual_end=cf.accrual_end,
                    )
                )
                matched_call_date = True
                break
            if cf.date > call_date:
                break
        if not matched_call_date:
            flows.append(
                BondCashFlow(
                    date=call_date,
                    amount=call_price,
                    flow_type=CashFlowType.PRINCIPAL,
                )
            )
        return flows

    def put_price_on(self, date: Date) -> Decimal | None:
        if self.put_schedule_data is None:
            return None
        return self.put_schedule_data.put_price_on(date, maturity_date=self.maturity_date())

    def cash_flows_to_put(self, put_date: Date) -> list[BondCashFlow]:
        """Return cash flows truncated at the put date and redeemed there."""
        put_price = self.put_price_on(put_date)
        if put_price is None:
            raise InvalidBondSpec(reason="put_date is not exercisable for this put schedule.")

        flows: list[BondCashFlow] = []
        matched_put_date = False
        for cf in self.base_bond.cash_flows():
            if cf.date < put_date:
                flows.append(cf)
                continue
            if cf.date == put_date:
                coupon_amount = cf.factored_amount()
                if cf.is_principal():
                    coupon_amount -= self.notional()
                flows.append(
                    BondCashFlow(
                        date=cf.date,
                        amount=coupon_amount + put_price,
                        flow_type=CashFlowType.COUPON_AND_PRINCIPAL,
                        accrual_start=cf.accrual_start,
                        accrual_end=cf.accrual_end,
                    )
                )
                matched_put_date = True
                break
            if cf.date > put_date:
                break
        if not matched_put_date:
            flows.append(
                BondCashFlow(
                    date=put_date,
                    amount=put_price,
                    flow_type=CashFlowType.PRINCIPAL,
                )
            )
        return flows

    def yield_to_maturity(self, clean_price: object, settlement_date: Date) -> Decimal:
        """Return the raw decimal yield to maturity."""
        from fuggers_py.bonds.pricing import BondPricer

        price = self._as_price(clean_price)
        return BondPricer().yield_from_price(self.base_bond, price, settlement_date).ytm.value()

    def yield_to_first_call(self, clean_price: object, settlement_date: Date) -> Decimal:
        """Return the raw decimal yield to the first future call."""
        if self.call_schedule is None:
            return self.yield_to_maturity(clean_price, settlement_date)
        entry = self.call_schedule.first_call_after(settlement_date)
        if entry is None:
            return self.yield_to_maturity(clean_price, settlement_date)
        return self.yield_to_call(clean_price, settlement_date, entry.call_date)

    def yield_to_call(self, clean_price: object, settlement_date: Date, call_date: Date) -> Decimal:
        """Return the raw decimal yield to the specified call date."""
        from fuggers_py.bonds.pricing import StandardYieldEngine

        price = self._as_price(clean_price)
        engine = StandardYieldEngine()
        result = engine.yield_from_price(
            self.cash_flows_to_call(call_date),
            clean_price=price.as_percentage(),
            accrued=self.accrued_interest(settlement_date),
            settlement_date=settlement_date,
            rules=self.rules(),
        )
        return Decimal(str(result.yield_rate))

    def yield_to_first_put(self, clean_price: object, settlement_date: Date) -> Decimal:
        """Return the raw decimal yield to the first future put."""
        if self.put_schedule_data is None:
            return self.yield_to_maturity(clean_price, settlement_date)
        entry = self.put_schedule_data.first_put_after(settlement_date)
        if entry is None:
            return self.yield_to_maturity(clean_price, settlement_date)
        return self.yield_to_put(clean_price, settlement_date, entry.put_date)

    def yield_to_put(self, clean_price: object, settlement_date: Date, put_date: Date) -> Decimal:
        """Return the raw decimal yield to the specified put date."""
        from fuggers_py.bonds.pricing import StandardYieldEngine

        price = self._as_price(clean_price)
        engine = StandardYieldEngine()
        result = engine.yield_from_price(
            self.cash_flows_to_put(put_date),
            clean_price=price.as_percentage(),
            accrued=self.accrued_interest(settlement_date),
            settlement_date=settlement_date,
            rules=self.rules(),
        )
        return Decimal(str(result.yield_rate))

    def yield_to_worst(self, clean_price: object, settlement_date: Date) -> Decimal:
        """Return the lowest raw decimal yield across maturity and workouts."""
        yields = [self.yield_to_maturity(clean_price, settlement_date)]
        if self.call_schedule is not None:
            for call_entry in self.call_schedule.future_entries(settlement_date):
                if self.call_schedule.is_protected(call_entry.call_date):
                    continue
                yields.append(self.yield_to_call(clean_price, settlement_date, call_entry.call_date))
        if self.put_schedule_data is not None:
            for put_entry in self.put_schedule_data.future_entries(settlement_date):
                yields.append(self.yield_to_put(clean_price, settlement_date, put_entry.put_date))
        return min(yields)

    def workout_dates(self, settlement_date: Date) -> list[Date]:
        """Return sorted future workout dates after settlement."""
        dates = {self.maturity_date()}
        if self.call_schedule is not None:
            dates.update(entry.call_date for entry in self.call_schedule.future_entries(settlement_date))
        if self.put_schedule_data is not None:
            dates.update(entry.put_date for entry in self.put_schedule_data.future_entries(settlement_date))
        return sorted(date for date in dates if date > settlement_date)

    def first_workout_date(self, settlement_date: Date) -> Date:
        """Return the earliest remaining workout date after settlement."""
        dates = self.workout_dates(settlement_date)
        if not dates:
            raise InvalidBondSpec(reason="No workout dates remain after settlement.")
        return dates[0]

    def yield_to_first_workout(self, clean_price: object, settlement_date: Date) -> Decimal:
        """Return the raw decimal yield to the first future workout date."""
        first_date = self.first_workout_date(settlement_date)
        if self.call_schedule is not None and self.call_price_on(first_date) is not None:
            return self.yield_to_call(clean_price, settlement_date, first_date)
        if self.put_schedule_data is not None and self.put_price_on(first_date) is not None:
            return self.yield_to_put(clean_price, settlement_date, first_date)
        return self.yield_to_maturity(clean_price, settlement_date)

    def _as_price(self, clean_price: object) -> Price:
        if isinstance(clean_price, Price):
            return clean_price
        return Price.new(_to_decimal(clean_price, field_name="clean_price"), self.currency())


@dataclass(slots=True)
class CallableBondBuilder:
    """Fluent builder for :class:`CallableBond`.

    The builder collects optional call and put entries and combines them with
    a required base bond before instantiation.
    """

    base_bond: FixedBond | None = None
    _entries: list[CallEntry] = field(default_factory=list)
    _put_entries: list[PutEntry] = field(default_factory=list)
    protection_end_date: Date | None = None

    @classmethod
    def new(cls) -> "CallableBondBuilder":
        return cls()

    def with_base_bond(self, bond: FixedBond) -> "CallableBondBuilder":
        self.base_bond = bond
        return self

    def with_call_schedule(self, schedule: CallSchedule) -> "CallableBondBuilder":
        self._entries = list(schedule.entries)
        self.protection_end_date = schedule.protection_end_date
        return self

    def with_put_schedule(self, schedule: PutSchedule) -> "CallableBondBuilder":
        self._put_entries = list(schedule.entries)
        return self

    def add_call(
        self,
        *,
        call_date: Date,
        call_price: object,
        call_type: CallType = CallType.EUROPEAN,
        call_end_date: Date | None = None,
        make_whole_spread: object | None = None,
    ) -> "CallableBondBuilder":
        self._entries.append(
            CallEntry(
                call_date=call_date,
                call_price=_to_decimal(call_price, field_name="call_price"),
                call_type=call_type,
                call_end_date=call_end_date,
                make_whole_spread=None
                if make_whole_spread is None
                else _to_decimal(make_whole_spread, field_name="make_whole_spread"),
            )
        )
        return self

    def with_protection_end_date(self, protection_end_date: Date) -> "CallableBondBuilder":
        self.protection_end_date = protection_end_date
        return self

    def add_put(
        self,
        *,
        put_date: Date,
        put_price: object,
        put_type: PutType = PutType.EUROPEAN,
        put_end_date: Date | None = None,
    ) -> "CallableBondBuilder":
        self._put_entries.append(
            PutEntry(
                put_date=put_date,
                put_price=_to_decimal(put_price, field_name="put_price"),
                put_type=put_type,
                put_end_date=put_end_date,
            )
        )
        return self

    def build(self) -> CallableBond:
        if self.base_bond is None:
            raise InvalidBondSpec(reason="base_bond is required.")
        if not self._entries and not self._put_entries:
            raise InvalidBondSpec(reason="at least one embedded option entry is required.")
        schedule = CallSchedule.new(self._entries, protection_end_date=self.protection_end_date) if self._entries else None
        put_schedule = PutSchedule.new(self._put_entries) if self._put_entries else None
        return CallableBond(base_bond=self.base_bond, call_schedule=schedule, put_schedule_data=put_schedule)


__all__ = [
    "CallEntry",
    "CallSchedule",
    "CallType",
    "CallableBond",
    "CallableBondBuilder",
    "PutEntry",
    "PutSchedule",
    "PutType",
]
