"""Credit product definitions.

The credit package currently exposes single-name CDS contract objects and
their premium-period helpers.
"""

from __future__ import annotations

from .cds import Cds, CdsPremiumPeriod, CreditDefaultSwap, ProtectionSide

__all__ = [
    "Cds",
    "CdsPremiumPeriod",
    "CreditDefaultSwap",
    "ProtectionSide",
]
