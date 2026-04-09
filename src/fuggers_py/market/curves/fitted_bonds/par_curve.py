"""Direct par-yield helpers built from fitted bond curves.

The canonical constant-maturity path in fitted-bond analytics should come
from the fitted discount or zero curve itself. This module therefore solves
for the coupon on a synthetic fixed-rate bond that prices to a target clean
price under the fitted curve, instead of proxying the curve through a
nearby-bond basket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence

from fuggers_py.core import Currency, Date, Frequency, Price
from fuggers_py.pricers.bonds import BondPricer
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.reference.bonds.types import YieldCalculationRules
from fuggers_py.market.curves.term_structure import TermStructure

from .fair_value import clean_price_from_curve, dirty_price_from_curve
from .bond_curve import BondCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class ParCurveSpec:
    """Convention bundle for a synthetic fitted-curve par bond.

    The synthetic bond is built from the fitted curve reference date unless an
    explicit issue or settlement date is supplied. The target price is a clean
    price in percent of par and defaults to 100.
    """

    frequency: Frequency = Frequency.SEMI_ANNUAL
    yield_rules: YieldCalculationRules = field(default_factory=YieldCalculationRules.us_treasury)
    currency: Currency = Currency.USD
    notional: Decimal = Decimal(100)
    price_target: Decimal = Decimal(100)
    settlement_date: Date | None = None
    issue_date: Date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "price_target", _to_decimal(self.price_target))
        if self.frequency.is_zero():
            raise ValueError("ParCurveSpec requires a non-zero coupon frequency.")
        if self.yield_rules.frequency != self.frequency:
            raise ValueError("ParCurveSpec yield_rules.frequency must match frequency.")
        if self.notional <= Decimal(0):
            raise ValueError("ParCurveSpec notional must be positive.")
        if self.price_target <= Decimal(0):
            raise ValueError("ParCurveSpec price_target must be positive.")
        if self.issue_date is not None and self.settlement_date is not None and self.issue_date > self.settlement_date:
            raise ValueError("ParCurveSpec issue_date must be on or before settlement_date when both are supplied.")


@dataclass(frozen=True, slots=True)
class FittedParYieldCurve:
    """Direct par-yield curve built from a fitted bond discount or zero curve."""

    curve: TermStructure
    spec: ParCurveSpec = field(default_factory=ParCurveSpec)
    pricer: BondPricer = field(default_factory=BondPricer)

    @classmethod
    def from_fit_result(
        cls,
        fit_result: BondCurve,
        spec: ParCurveSpec | None = None,
    ) -> "FittedParYieldCurve":
        """Construct a direct par-yield curve from a fitted-bond result."""

        return cls(curve=fit_result, spec=spec or ParCurveSpec())

    def date(self) -> Date:
        """Return the fitted-curve date."""

        return self.curve.date()

    def settlement_date(self) -> Date:
        """Return the settlement date used for synthetic par-bond pricing."""

        return self.spec.settlement_date or self.date()

    def issue_date(self) -> Date:
        """Return the issue date used to generate synthetic bond schedules."""

        return self.spec.issue_date or self.settlement_date()

    def maturity_date(self, tenor_years: object) -> Date:
        """Return the synthetic bond maturity date for ``tenor_years``."""

        tenor = _to_decimal(tenor_years)
        if tenor <= Decimal(0):
            raise ValueError("FittedParYieldCurve requires a positive tenor_years input.")
        maturity = self.settlement_date().add_days(int(round(float(tenor) * 365.0)))
        if maturity <= self.issue_date():
            raise ValueError("FittedParYieldCurve tenor_years must imply a maturity after issue_date.")
        return maturity

    def synthetic_bond(self, tenor_years: object, coupon_rate: object | None = None) -> Bond:
        """Return the synthetic fixed-rate bond for ``tenor_years``.

        When ``coupon_rate`` is omitted, the method uses the direct par yield
        implied by the fitted curve.
        """

        resolved_coupon = self.par_yield(tenor_years) if coupon_rate is None else _to_decimal(coupon_rate)
        return (
            FixedBondBuilder.new()
            .with_issue_date(self.issue_date())
            .with_maturity_date(self.maturity_date(tenor_years))
            .with_coupon_rate(resolved_coupon)
            .with_frequency(self.spec.frequency)
            .with_currency(self.spec.currency)
            .with_notional(self.spec.notional)
            .with_rules(self.spec.yield_rules)
            .build()
        )

    def clean_price(self, tenor_years: object, coupon_rate: object | None = None) -> Decimal:
        """Return the fitted clean price of the synthetic bond."""

        bond = self.synthetic_bond(tenor_years, coupon_rate)
        return clean_price_from_curve(
            bond,
            self.curve,
            self.settlement_date(),
        )

    def dirty_price(self, tenor_years: object, coupon_rate: object | None = None) -> Decimal:
        """Return the fitted dirty price of the synthetic bond."""

        bond = self.synthetic_bond(tenor_years, coupon_rate)
        return dirty_price_from_curve(
            bond,
            self.curve,
            self.settlement_date(),
        )

    def yield_to_maturity(self, tenor_years: object, coupon_rate: object | None = None) -> Decimal:
        """Return the fitted market yield of the synthetic bond."""

        bond = self.synthetic_bond(tenor_years, coupon_rate)
        clean_price = self.clean_price(tenor_years, coupon_rate)
        return self.pricer.yield_from_price(
            bond,
            Price.new(clean_price, bond.currency()),
            self.settlement_date(),
        ).ytm.value()

    def par_yield(self, tenor_years: object) -> Decimal:
        """Return the direct par yield at ``tenor_years``.

        The clean price under the fitted curve is affine in coupon for a fixed
        schedule, so the par coupon can be solved exactly from two synthetic
        price evaluations.
        """

        zero_coupon_price = self.clean_price(tenor_years, Decimal(0))
        unit_coupon_price = self.clean_price(tenor_years, Decimal(1))
        coupon_sensitivity = unit_coupon_price - zero_coupon_price
        if coupon_sensitivity == Decimal(0):
            raise ValueError("FittedParYieldCurve par-yield solve requires non-zero coupon sensitivity.")
        return (self.spec.price_target - zero_coupon_price) / coupon_sensitivity

    def sample(self, tenors: Sequence[object]) -> tuple[Decimal, ...]:
        """Return par yields for ``tenors`` in the input order."""

        return tuple(self.par_yield(tenor) for tenor in tenors)


__all__ = ["FittedParYieldCurve", "ParCurveSpec"]
