"""Deliverable basket objects for government bond futures.

Deliverable bonds carry clean prices in percent of par and can be converted to
futures-equivalent prices, yields, and dirty prices using the settlement date
passed to the helper methods. The basket preserves a deterministic order so
pricing and conversion-factor workflows are reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from fuggers_py.bonds.instruments import FixedBondBuilder
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core.compounding import CompoundingKind
from fuggers_py._core.types import Compounding, Currency, Date, Frequency, Price, Yield
from fuggers_py._core.ids import InstrumentId

from .reference import DeliverableBondReference

if TYPE_CHECKING:
    from fuggers_py.bonds import BondPricer


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_currency(value: Currency | str) -> Currency:
    if isinstance(value, Currency):
        return value
    return Currency.from_code(str(value))


def _coerce_frequency(value: Frequency | str) -> Frequency:
    if isinstance(value, Frequency):
        return value
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "ANNUAL": Frequency.ANNUAL,
        "YEARLY": Frequency.ANNUAL,
        "SEMIANNUAL": Frequency.SEMI_ANNUAL,
        "SEMI_ANNUAL": Frequency.SEMI_ANNUAL,
        "SEMI": Frequency.SEMI_ANNUAL,
        "QUARTERLY": Frequency.QUARTERLY,
        "QUARTER": Frequency.QUARTERLY,
        "MONTHLY": Frequency.MONTHLY,
        "MONTH": Frequency.MONTHLY,
        "ZERO": Frequency.ZERO,
    }
    if normalized in aliases:
        return aliases[normalized]
    return Frequency[normalized]


def _yield_compounding(rules: YieldCalculationRules) -> Compounding:
    """Map bond yield rules onto the yield-compounding enum used by pricers."""
    method = rules.compounding
    if method.kind is CompoundingKind.CONTINUOUS:
        return Compounding.CONTINUOUS
    if method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        return Compounding.SIMPLE
    if method.frequency == 1:
        return Compounding.ANNUAL
    if method.frequency == 2:
        return Compounding.SEMI_ANNUAL
    if method.frequency == 4:
        return Compounding.QUARTERLY
    if method.frequency == 12:
        return Compounding.MONTHLY
    return Compounding.ANNUAL


@dataclass(frozen=True, slots=True)
class DeliverableBond:
    """A bond deliverable into a government bond futures contract.

    Parameters
    ----------
    clean_price
        Clean price quoted in percent of par.
    coupon_rate
        Coupon rate as a raw decimal.
    notional
        Bond face amount in currency units.
    published_conversion_factor
        Optional exchange-published conversion factor, if available.

    Notes
    -----
    ``clean_price`` is quoted in percent of par. Yield calculations reuse the
    bond pricer rules aligned to the bond's coupon frequency.
    """

    instrument_id: InstrumentId
    issue_date: Date
    maturity_date: Date
    coupon_rate: Decimal
    clean_price: Decimal
    currency: Currency | str = Currency.USD
    frequency: Frequency | str = Frequency.SEMI_ANNUAL
    notional: Decimal = Decimal(100)
    yield_rules: YieldCalculationRules | None = None
    published_conversion_factor: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "coupon_rate", _to_decimal(self.coupon_rate))
        object.__setattr__(self, "clean_price", _to_decimal(self.clean_price))
        object.__setattr__(self, "currency", _coerce_currency(self.currency))
        object.__setattr__(self, "frequency", _coerce_frequency(self.frequency))
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        if self.published_conversion_factor is not None:
            object.__setattr__(
                self,
                "published_conversion_factor",
                _to_decimal(self.published_conversion_factor),
            )
        if self.maturity_date <= self.issue_date:
            raise ValueError("DeliverableBond requires maturity_date after issue_date.")
        if self.notional <= Decimal(0):
            raise ValueError("DeliverableBond notional must be positive.")
        if self.clean_price <= Decimal(0):
            raise ValueError("DeliverableBond clean_price must be positive.")
        if self.published_conversion_factor is not None and self.published_conversion_factor <= Decimal(0):
            raise ValueError("DeliverableBond published_conversion_factor must be positive when supplied.")

    @classmethod
    def from_reference(cls, reference: DeliverableBondReference, *, clean_price: object) -> "DeliverableBond":
        """Build a deliverable bond from reference data and a live clean price."""
        return cls(
            instrument_id=reference.instrument_id,
            issue_date=reference.issue_date,
            maturity_date=reference.maturity_date,
            coupon_rate=reference.coupon_rate,
            clean_price=clean_price,
            currency=reference.currency,
            frequency=reference.frequency,
            notional=reference.notional,
            yield_rules=reference.yield_rules,
            published_conversion_factor=reference.published_conversion_factor,
        )

    def reference(self) -> DeliverableBondReference:
        """Return the reference-data view of the bond."""
        return DeliverableBondReference(
            instrument_id=self.instrument_id,
            issue_date=self.issue_date,
            maturity_date=self.maturity_date,
            coupon_rate=self.coupon_rate,
            currency=self.currency,
            frequency=self.frequency,
            notional=self.notional,
            yield_rules=self.yield_rules,
            published_conversion_factor=self.published_conversion_factor,
        )

    def rules(self) -> YieldCalculationRules:
        """Return yield rules aligned to the bond coupon frequency."""
        rules = self.yield_rules or YieldCalculationRules.us_treasury()
        if rules.frequency is self.frequency:
            return rules
        return replace(rules, frequency=self.frequency)

    def to_bond(self):
        """Build the corresponding fixed-coupon bond instrument."""
        return (
            FixedBondBuilder.new()
            .with_issue_date(self.issue_date)
            .with_maturity_date(self.maturity_date)
            .with_coupon_rate(self.coupon_rate)
            .with_frequency(self.frequency)
            .with_currency(self.currency)
            .with_notional(self.notional)
            .with_instrument_id(self.instrument_id)
            .with_rules(self.rules())
            .build()
        )

    def accrued_interest(self, settlement_date: Date) -> Decimal:
        """Return accrued interest at `settlement_date` in currency units."""
        return self.to_bond().accrued_interest(settlement_date)

    def dirty_price(self, settlement_date: Date) -> Decimal:
        """Return dirty price as clean price plus accrued interest."""
        return self.clean_price + self.accrued_interest(settlement_date)

    def yield_to_maturity(self, settlement_date: Date, *, pricer: BondPricer | None = None) -> Decimal:
        """Return the bond yield as a raw decimal."""
        from fuggers_py.bonds import BondPricer

        resolved_pricer = pricer or BondPricer()
        result = resolved_pricer.yield_from_price(
            self.to_bond(),
            Price.new(self.clean_price, self.currency),
            settlement_date,
        )
        return result.ytm.value()

    def price_from_yield(
        self,
        yield_rate: object,
        settlement_date: Date,
        *,
        pricer: BondPricer | None = None,
    ) -> Decimal:
        """Return the clean price implied by a raw-decimal yield."""
        from fuggers_py.bonds import BondPricer

        resolved_pricer = pricer or BondPricer()
        result = resolved_pricer.price_from_yield(
            self.to_bond(),
            Yield.new(_to_decimal(yield_rate), _yield_compounding(self.rules())),
            settlement_date,
        )
        return result.clean.as_percentage()

    def price_with_yield_shift(
        self,
        settlement_date: Date,
        *,
        base_settlement_date: Date,
        yield_shift_bps: object = Decimal(0),
        pricer: BondPricer | None = None,
    ) -> Decimal:
        """Return the clean price after shifting the yield by basis points."""
        shift = _to_decimal(yield_shift_bps) / Decimal("10000")
        base_yield = self.yield_to_maturity(base_settlement_date, pricer=pricer)
        return self.price_from_yield(base_yield + shift, settlement_date, pricer=pricer)


@dataclass(frozen=True, slots=True)
class DeliverableBasket:
    """Ordered deliverable basket for a government bond futures contract."""

    as_of: Date
    deliverables: tuple[DeliverableBond, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.deliverables:
            raise ValueError("DeliverableBasket requires at least one deliverable bond.")
        ordered = tuple(sorted(self.deliverables, key=lambda item: item.instrument_id.as_str()))
        object.__setattr__(self, "deliverables", ordered)
        seen: set[InstrumentId] = set()
        currencies = {bond.currency for bond in ordered}
        for bond in ordered:
            if bond.instrument_id in seen:
                raise ValueError("DeliverableBasket instrument_ids must be unique.")
            seen.add(bond.instrument_id)
        if len(currencies) != 1:
            raise ValueError("DeliverableBasket requires a common currency across deliverables.")

    def currency(self) -> Currency:
        """Return the common basket currency."""
        return self.deliverables[0].currency

    def instrument_ids(self) -> tuple[InstrumentId, ...]:
        """Return basket instrument identifiers in deterministic order."""
        return tuple(bond.instrument_id for bond in self.deliverables)

    def get_deliverable(self, instrument_id: InstrumentId | str) -> DeliverableBond:
        """Return the deliverable matching `instrument_id`."""
        resolved = InstrumentId.parse(instrument_id)
        for bond in self.deliverables:
            if bond.instrument_id == resolved:
                return bond
        raise KeyError(f"Unknown deliverable instrument_id: {resolved}.")


__all__ = ["DeliverableBasket", "DeliverableBond"]
