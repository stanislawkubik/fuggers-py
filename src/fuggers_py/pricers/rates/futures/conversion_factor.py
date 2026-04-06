"""Conversion-factor helpers for government bond futures.

The theoretical conversion factor is the deliverable bond clean price at the
contract's standardized coupon rate, normalized by par. Published conversion
factors override the theoretical value when requested.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.pricers.bonds import BondPricer
from fuggers_py.core.ids import InstrumentId
from fuggers_py.products.rates.futures import DeliverableBond, GovernmentBondFuture


@dataclass(frozen=True, slots=True)
class ConversionFactorResult:
    """Comparison between theoretical and published conversion factors.

    The values are unitless decimals. When a published conversion factor is
    present and selected, `used_published_override` identifies that choice.
    """

    instrument_id: InstrumentId
    delivery_date: object
    theoretical_conversion_factor: Decimal
    conversion_factor: Decimal
    published_conversion_factor: Decimal | None = None

    @property
    def used_published_override(self) -> bool:
        """Return whether the published conversion factor was selected."""
        return self.published_conversion_factor is not None and self.conversion_factor == self.published_conversion_factor


def theoretical_conversion_factor(
    contract: GovernmentBondFuture,
    deliverable: DeliverableBond,
    *,
    pricer: BondPricer | None = None,
) -> Decimal:
    """Return the theoretical conversion factor as a unitless decimal."""
    delivery_date = contract.resolved_delivery_date()
    clean_price = deliverable.price_from_yield(contract.standard_coupon_rate, delivery_date, pricer=pricer)
    factor = clean_price / Decimal(100)
    if factor <= Decimal(0):
        raise ValueError("Theoretical conversion factor must be positive.")
    return factor


def conversion_factor(
    contract: GovernmentBondFuture,
    deliverable: DeliverableBond,
    *,
    prefer_published_override: bool = True,
    pricer: BondPricer | None = None,
) -> ConversionFactorResult:
    """Return the selected conversion factor and the theoretical reference."""
    theoretical = theoretical_conversion_factor(contract, deliverable, pricer=pricer)
    published = deliverable.published_conversion_factor
    selected = published if prefer_published_override and published is not None else theoretical
    if selected <= Decimal(0):
        raise ValueError("Conversion factor must be positive.")
    return ConversionFactorResult(
        instrument_id=deliverable.instrument_id,
        delivery_date=contract.resolved_delivery_date(),
        theoretical_conversion_factor=theoretical,
        conversion_factor=selected,
        published_conversion_factor=published,
    )


__all__ = ["ConversionFactorResult", "conversion_factor", "theoretical_conversion_factor"]
