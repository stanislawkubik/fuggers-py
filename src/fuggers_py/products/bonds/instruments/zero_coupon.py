"""Zero-coupon bond instruments.

The zero-coupon bond only returns principal at maturity. It reuses the same
yield rules and schedule machinery as coupon-bearing bonds so that pricing and
settlement behavior stay aligned with the rest of the bond layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar

from fuggers_py.core.ids import InstrumentId
from fuggers_py.core.types import Currency, Date, Frequency
from fuggers_py.products.instruments import KindedInstrumentMixin

from ..cashflows import CashFlowGenerator, Schedule, ScheduleConfig
from fuggers_py.reference.bonds.errors import InvalidBondSpec
from ..traits import Bond, BondAnalytics, BondCashFlow
from fuggers_py.reference.bonds.types import BondIdentifiers, YieldCalculationRules


@dataclass(frozen=True, slots=True)
class ZeroCouponBond(KindedInstrumentMixin, BondAnalytics, Bond):
    """Bond that pays principal only at maturity.

    Parameters
    ----------
    _issue_date, _maturity_date:
        Bond issue and maturity dates.
    _currency:
        Bond currency.
    _notional:
        Face amount repaid at maturity.
    _identifiers:
        Optional identifier set.
    _rules:
        Yield and accrual rules.
    instrument_id:
        Optional stable instrument identifier.
    """

    KIND: ClassVar[str] = "bond.zero_coupon"

    _issue_date: Date
    _maturity_date: Date
    _currency: Currency = Currency.USD
    _notional: Decimal = Decimal(100)
    _identifiers: BondIdentifiers = field(default_factory=BondIdentifiers)
    _rules: YieldCalculationRules = field(default_factory=YieldCalculationRules.us_treasury)
    instrument_id: InstrumentId | None = None

    _schedule: Schedule = field(init=False, repr=False)
    _cashflows: list[BondCashFlow] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self._maturity_date <= self._issue_date:
            raise InvalidBondSpec(reason="maturity_date must be after issue_date.")
        if self._notional <= 0:
            raise InvalidBondSpec(reason="notional must be positive.")

        rules = self.rules()
        schedule_config = ScheduleConfig(
            start_date=self._issue_date,
            end_date=self._maturity_date,
            frequency=Frequency.ZERO,
            calendar=rules.calendar,
            business_day_convention=rules.business_day_convention,
            end_of_month=rules.end_of_month,
            stub_rules=rules.stub_rules,
        )
        schedule = Schedule.generate(schedule_config)
        cashflows = CashFlowGenerator.fixed_rate_bond_cashflows(
            schedule=schedule,
            coupon_rate=Decimal(0),
            notional=self._notional,
            rules=rules,
        )
        object.__setattr__(self, "_schedule", schedule)
        object.__setattr__(self, "_cashflows", cashflows)

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
        return Frequency.ZERO

    def rules(self) -> YieldCalculationRules:
        return self._rules

    def cash_flows(self, from_date: Date | None = None) -> list[BondCashFlow]:
        return CashFlowGenerator.future_cashflows(self._cashflows, from_date)

    def accrued_interest(self, settlement_date: Date) -> Decimal:
        """Zero-coupon bonds do not accrue interest between issuance and maturity."""
        return Decimal(0)


__all__ = ["ZeroCouponBond"]
