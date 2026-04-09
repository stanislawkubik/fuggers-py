"""Dedicated zero-breakeven and par-breakeven curve objects."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Sequence

from fuggers_py.core import Compounding, Date
from fuggers_py.core.traits import YieldCurve as CoreYieldCurve

from ..conversion import ValueConverter
from ..term_structure import TermStructure
from ..fitted_bonds.fair_value import _discount_factor_from_curve
from ..fitted_bonds.par_curve import FittedParYieldCurve

if TYPE_CHECKING:
    from ..fitted_bonds.bond_curve import BondCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _tenor(value: object) -> Decimal:
    tenor = _to_decimal(value)
    if tenor < Decimal(0):
        raise ValueError("Breakeven curve tenor inputs must be non-negative.")
    return tenor


@dataclass(frozen=True, slots=True)
class BreakevenZeroCurve(TermStructure):
    """Zero-breakeven curve derived from nominal and real fitted curves.

    The curve exposes zero breakevens as rate values and also exposes the
    implied inflation accumulation factor through ``discount_factor(...)``.
    That factor is the ratio ``real_df / nominal_df`` and can therefore be
    greater than 1 when implied inflation is positive.
    """

    nominal_curve: CoreYieldCurve | TermStructure
    real_curve: CoreYieldCurve | TermStructure
    compounding: Compounding = Compounding.CONTINUOUS

    def __post_init__(self) -> None:
        if self.nominal_curve.date() != self.real_curve.date():
            raise ValueError("BreakevenZeroCurve requires nominal and real curves with the same reference_date.")

    @classmethod
    def from_fitted_curves(
        cls,
        nominal_fit_result: BondCurve,
        real_fit_result: BondCurve,
        *,
        compounding: Compounding = Compounding.CONTINUOUS,
    ) -> "BreakevenZeroCurve":
        """Construct a zero-breakeven curve from fitted nominal and real curves."""

        return cls(
            nominal_curve=nominal_fit_result,
            real_curve=real_fit_result,
            compounding=compounding,
        )

    @staticmethod
    def rate_from_zero_rates(
        *,
        nominal_rate: object,
        real_rate: object,
        compounding: Compounding = Compounding.CONTINUOUS,
    ) -> Decimal:
        """Return the compounding-consistent breakeven from two zero rates."""

        nominal_decimal = _to_decimal(nominal_rate)
        real_decimal = _to_decimal(real_rate)
        if compounding is Compounding.CONTINUOUS:
            return nominal_decimal - real_decimal
        nominal = float(nominal_decimal)
        real = float(real_decimal)
        nominal_continuous = ValueConverter.convert_compounding(nominal, compounding, Compounding.CONTINUOUS)
        real_continuous = ValueConverter.convert_compounding(real, compounding, Compounding.CONTINUOUS)
        breakeven_continuous = nominal_continuous - real_continuous
        breakeven = ValueConverter.convert_compounding(
            breakeven_continuous,
            Compounding.CONTINUOUS,
            compounding,
        )
        return Decimal(str(breakeven))

    def date(self) -> Date:
        """Return the shared curve date."""

        return self.nominal_curve.date()

    def discount_factor(self, tenor_years: object) -> Decimal:
        """Return the implied inflation accumulation factor at ``tenor_years``."""

        tenor = _tenor(tenor_years)
        if tenor == Decimal(0):
            return Decimal(1)
        nominal_df = _discount_factor_from_curve(self.nominal_curve, self.date().add_days(int(round(float(tenor) * 365.0))))
        real_df = _discount_factor_from_curve(self.real_curve, self.date().add_days(int(round(float(tenor) * 365.0))))
        if nominal_df <= Decimal(0) or real_df <= Decimal(0):
            raise ValueError("BreakevenZeroCurve requires positive nominal and real discount factors.")
        return real_df / nominal_df

    def zero_breakeven(self, tenor_years: object) -> Decimal:
        """Return the zero breakeven at ``tenor_years``."""

        tenor = _tenor(tenor_years)
        if tenor == Decimal(0):
            return Decimal(0)
        inflation_factor = self.discount_factor(tenor)
        continuous_rate = math.log(float(inflation_factor)) / float(tenor)
        breakeven = ValueConverter.convert_compounding(
            continuous_rate,
            Compounding.CONTINUOUS,
            self.compounding,
        )
        return Decimal(str(breakeven))

    def value_at_tenor(self, t: float) -> float:
        """Return the configured zero breakeven at tenor ``t``."""

        return float(self.zero_breakeven(Decimal(str(float(t)))))

    def sample(self, tenors: Sequence[object]) -> tuple[Decimal, ...]:
        """Return zero breakevens for ``tenors`` in input order."""

        return tuple(self.zero_breakeven(tenor) for tenor in tenors)


@dataclass(frozen=True, slots=True)
class BreakevenParCurve:
    """Par-breakeven curve derived from nominal and real par curves."""

    nominal_curve: FittedParYieldCurve
    real_curve: FittedParYieldCurve

    def __post_init__(self) -> None:
        if self.nominal_curve.date() != self.real_curve.date():
            raise ValueError("BreakevenParCurve requires nominal and real par curves with the same reference_date.")
        if self.nominal_curve.spec.frequency != self.real_curve.spec.frequency:
            raise ValueError("BreakevenParCurve requires matching nominal and real coupon frequencies.")
        if self.nominal_curve.spec.yield_rules.compounding != self.real_curve.spec.yield_rules.compounding:
            raise ValueError("BreakevenParCurve requires matching nominal and real par-yield compounding.")
        if self.nominal_curve.spec.price_target != self.real_curve.spec.price_target:
            raise ValueError("BreakevenParCurve requires matching nominal and real par price targets.")

    @classmethod
    def from_par_curves(
        cls,
        nominal_curve: FittedParYieldCurve,
        real_curve: FittedParYieldCurve,
    ) -> "BreakevenParCurve":
        """Construct a par-breakeven curve from nominal and real par curves."""

        return cls(nominal_curve=nominal_curve, real_curve=real_curve)

    def date(self) -> Date:
        """Return the shared par-curve date."""

        return self.nominal_curve.date()

    def par_breakeven(self, tenor_years: object) -> Decimal:
        """Return the par breakeven at ``tenor_years``."""

        tenor = _tenor(tenor_years)
        return self.nominal_curve.par_yield(tenor) - self.real_curve.par_yield(tenor)

    def sample(self, tenors: Sequence[object]) -> tuple[Decimal, ...]:
        """Return par breakevens for ``tenors`` in input order."""

        return tuple(self.par_breakeven(tenor) for tenor in tenors)


__all__ = ["BreakevenParCurve", "BreakevenZeroCurve"]
