"""Bond-versus-CDS basis helpers.

The basis is computed from a cash-bond spread minus an adjusted CDS spread,
all as raw decimal rates.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .adjusted_cds import adjusted_cds_breakdown


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class BondCdsBasisBreakdown:
    """Break down the bond/CDS basis calculation.

    Attributes
    ----------
    bond_spread:
        Cash-bond spread in raw decimal form.
    quoted_cds_spread:
        CDS spread before adjustments.
    adjusted_cds_spread:
        CDS spread after removing non-default-risk adjustments.
    delivery_option_adjustment:
        Delivery-option component removed from the quote.
    fx_adjustment:
        FX component removed from the quote.
    other_cds_adjustment:
        Other component removed from the quote.
    basis:
        Cash-bond spread minus adjusted CDS spread.
    """

    bond_spread: Decimal
    quoted_cds_spread: Decimal
    adjusted_cds_spread: Decimal
    delivery_option_adjustment: Decimal
    fx_adjustment: Decimal
    other_cds_adjustment: Decimal
    basis: Decimal


def bond_cds_basis_breakdown(
    *,
    bond_spread: object,
    cds_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_cds_adjustment: object = Decimal(0),
) -> BondCdsBasisBreakdown:
    """Compute a cash-bond versus CDS basis.

    Returns
    -------
    BondCdsBasisBreakdown
        Full breakdown of the bond spread, adjusted CDS spread, and basis.

    Positive basis means the cash bond spread is wider than the adjusted CDS
    spread. Negative basis means the bond is rich versus CDS.
    """

    bond = _to_decimal(bond_spread)
    breakdown = adjusted_cds_breakdown(
        quoted_spread=cds_spread,
        delivery_option_adjustment=delivery_option_adjustment,
        fx_adjustment=fx_adjustment,
        other_adjustment=other_cds_adjustment,
    )
    return BondCdsBasisBreakdown(
        bond_spread=bond,
        quoted_cds_spread=breakdown.quoted_spread,
        adjusted_cds_spread=breakdown.adjusted_spread,
        delivery_option_adjustment=breakdown.delivery_option_adjustment,
        fx_adjustment=breakdown.fx_adjustment,
        other_cds_adjustment=breakdown.other_adjustment,
        basis=bond - breakdown.adjusted_spread,
    )


def bond_cds_basis(
    *,
    bond_spread: object,
    cds_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_cds_adjustment: object = Decimal(0),
) -> Decimal:
    """Return the cash-bond versus CDS basis as a raw decimal.

    Positive values mean the cash bond spread is wider than the adjusted CDS
    spread.
    """

    return bond_cds_basis_breakdown(
        bond_spread=bond_spread,
        cds_spread=cds_spread,
        delivery_option_adjustment=delivery_option_adjustment,
        fx_adjustment=fx_adjustment,
        other_cds_adjustment=other_cds_adjustment,
    ).basis


__all__ = [
    "BondCdsBasisBreakdown",
    "bond_cds_basis",
    "bond_cds_basis_breakdown",
]
