"""CDS risk helpers."""

from __future__ import annotations

from decimal import Decimal

from .instruments import CreditDefaultSwap
from .pricing import CdsPricer


def risky_pv01(cds: CreditDefaultSwap, curves: object, *, pricer: CdsPricer | None = None) -> Decimal:
    """Return the CDS risky PV01 from the credit and discount curves."""

    return (pricer or CdsPricer()).risky_pv01(cds, curves)


def cds_cs01(cds: CreditDefaultSwap, curves: object, *, pricer: CdsPricer | None = None) -> Decimal:
    """Return the signed one-basis-point CDS spread sensitivity."""

    return (pricer or CdsPricer()).cs01(cds, curves)


cs01 = cds_cs01


__all__ = [
    "cds_cs01",
    "cs01",
    "risky_pv01",
]
