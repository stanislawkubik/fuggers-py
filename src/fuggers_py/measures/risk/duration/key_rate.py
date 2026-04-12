"""Key-rate duration helpers (`fuggers_py.measures.risk.duration.key_rate`).

These helpers bump one tenor at a time and return positive-magnitude key-rate
duration exposures on the supplied tenor grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.types import Date
from fuggers_py.market.curve_support import STANDARD_KEY_RATE_TENORS, key_rate_bumped_curve
from fuggers_py.market.curves import DiscountingCurve
from fuggers_py.measures.pricing import BondPricer


def _tenor_years(tenor: Tenor) -> float:
    return float(tenor.to_years_approx())


@dataclass(frozen=True, slots=True)
class KeyRateDuration:
    """Key-rate duration exposure at a specific tenor.

    Parameters
    ----------
    tenor:
        Tenor at which the curve was bumped.
    duration:
        Key-rate duration exposure in years.
    """

    tenor: Tenor
    duration: Decimal


@dataclass(frozen=True, slots=True)
class KeyRateDurations:
    """Collection of key-rate duration exposures.

    Attributes
    ----------
    items:
        Ordered list of tenor-specific duration exposures.
    """

    items: list[KeyRateDuration]

    def as_dict(self) -> dict[Tenor, Decimal]:
        """Return the exposures as a tenor-to-duration mapping."""

        return {item.tenor: item.duration for item in self.items}


@dataclass(frozen=True, slots=True)
class KeyRateDurationCalculator:
    """Calculate tenor-specific duration exposures using symmetric bumps.

    Parameters
    ----------
    bump:
        Symmetric curve bump in raw decimal units. ``1e-4`` means 1 bp.
    """

    bump: float = 1e-4

    def calculate(
        self,
        bond: Bond,
        curve: DiscountingCurve,
        settlement_date: Date,
        tenors: list[Tenor] | None = None,
    ) -> KeyRateDurations:
        """Return key-rate durations for the requested tenor grid.

        The returned exposures are ordered by tenor after de-duplicating the
        requested grid.
        """

        grid = tenors or list(STANDARD_KEY_RATE_TENORS)
        grid = sorted(set(grid), key=_tenor_years)
        if not grid:
            raise ValueError("Key-rate duration requires a non-empty tenor grid.")

        pricer = BondPricer()
        p0 = pricer.price_from_curve(bond, curve, settlement_date).dirty.as_percentage()
        if p0 == 0:
            return KeyRateDurations(items=[])

        items: list[KeyRateDuration] = []
        for tenor in grid:
            kr_up = key_rate_bumped_curve(curve, tenor_grid=grid, key_tenor=tenor, bump=self.bump)
            kr_dn = key_rate_bumped_curve(curve, tenor_grid=grid, key_tenor=tenor, bump=-self.bump)

            p_up = pricer.price_from_curve(bond, kr_up, settlement_date).dirty.as_percentage()
            p_dn = pricer.price_from_curve(bond, kr_dn, settlement_date).dirty.as_percentage()

            duration = (p_dn - p_up) / (Decimal(2) * p0 * Decimal(str(self.bump)))
            items.append(KeyRateDuration(tenor=tenor, duration=duration))

        return KeyRateDurations(items=items)


def key_rate_duration_at_tenor(
    bond: Bond,
    curve: DiscountingCurve,
    settlement_date: Date,
    *,
    tenor: Tenor,
    bump: float = 1e-4,
    tenor_grid: list[Tenor] | None = None,
) -> Decimal:
    """Return the key-rate duration exposure for a single tenor.

    Returns
    -------
    Decimal
        Key-rate duration for the requested tenor. Returns zero when the tenor
        is not present in the computed grid.
    """

    grid = list(tenor_grid) if tenor_grid is not None else list(STANDARD_KEY_RATE_TENORS)
    if tenor not in grid:
        grid = sorted(grid + [tenor], key=_tenor_years)

    calc = KeyRateDurationCalculator(bump=bump)
    result = calc.calculate(bond, curve, settlement_date, tenors=grid)
    for item in result.items:
        if item.tenor == tenor:
            return item.duration
    return Decimal(0)


__all__ = [
    "KeyRateDuration",
    "KeyRateDurations",
    "KeyRateDurationCalculator",
    "key_rate_duration_at_tenor",
]
