"""Risk calculators (`fuggers_py._measures.risk.calculator`).

The calculator classes combine duration, convexity, and DV01 helpers into
aggregated bond-risk summaries. The outputs follow the positive-magnitude
convention used throughout the analytics package.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._pricers.bonds import BondPricer as _BondPricer
from fuggers_py._products.bonds.traits import Bond
from fuggers_py._core.types import Date, Yield

from .convexity import analytical_convexity
from .duration import DEFAULT_BUMP_SIZE, effective_duration, macaulay_duration, modified_duration
from .dv01 import dv01_per_100_face


@dataclass(frozen=True, slots=True)
class BondRiskMetrics:
    """Bundle of bond-risk measures returned by the calculator.

    Attributes
    ----------
    modified_duration:
        Positive modified duration in years.
    macaulay_duration:
        Positive Macaulay duration in years.
    convexity:
        Positive convexity magnitude.
    dv01:
        Positive DV01 in currency units for a 1 bp move.
    """

    modified_duration: Decimal
    macaulay_duration: Decimal
    convexity: Decimal
    dv01: Decimal


@dataclass(frozen=True, slots=True)
class EffectiveDurationCalculator:
    """Helper that computes effective duration with a configurable bump.

    Parameters
    ----------
    bump:
        Symmetric yield bump in raw decimal units. ``1e-4`` means 1 bp.
    """

    bump: float = DEFAULT_BUMP_SIZE

    def calculate(self, bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
        """Return effective duration using the configured bump size."""

        return effective_duration(bond, ytm, settlement_date, bump=self.bump)


@dataclass(frozen=True, slots=True)
class BondRiskCalculator:
    """Compute standard risk measures for a single bond.

    Parameters
    ----------
    bond:
        Bond to analyze.
    ytm:
        Yield used for the risk calculations.
    settlement_date:
        Settlement date used to filter future cash flows.
    bump:
        Symmetric yield bump in raw decimal units for effective measures.
    """

    bond: Bond
    ytm: Yield
    settlement_date: Date
    bump: float = DEFAULT_BUMP_SIZE

    def modified_duration(self) -> Decimal:
        """Return modified duration as a positive magnitude."""

        return modified_duration(self.bond, self.ytm, self.settlement_date)

    def macaulay_duration(self) -> Decimal:
        """Return Macaulay duration as a positive magnitude."""

        return macaulay_duration(self.bond, self.ytm, self.settlement_date)

    def convexity(self) -> Decimal:
        """Return analytical convexity, falling back to the effective path."""

        return analytical_convexity(self.bond, self.ytm, self.settlement_date)

    def dv01(self) -> Decimal:
        """Return DV01 as a positive currency PV change for a 1 bp move."""

        pricer = _BondPricer()
        rules = self.bond.rules()
        y = float(pricer._yield_to_engine_rate(self.ytm, rules=rules))
        dirty = pricer.engine.dirty_price_from_yield(
            self.bond.cash_flows(),
            yield_rate=y,
            settlement_date=self.settlement_date,
            rules=rules,
        )
        md = self.modified_duration()
        return dv01_per_100_face(md, Decimal(str(dirty)))

    def all_metrics(self) -> BondRiskMetrics:
        """Return the full risk bundle for the configured bond."""

        return BondRiskMetrics(
            modified_duration=self.modified_duration(),
            macaulay_duration=self.macaulay_duration(),
            convexity=self.convexity(),
            dv01=self.dv01(),
        )


__all__ = [
    "BondRiskCalculator",
    "BondRiskMetrics",
    "EffectiveDurationCalculator",
]
