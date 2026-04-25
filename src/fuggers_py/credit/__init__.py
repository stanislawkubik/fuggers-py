"""First-layer public facade for credit-domain objects."""

from __future__ import annotations

from .analytics import (
    AdjustedCdsBreakdown,
    BondCdsBasisBreakdown,
    RiskFreeProxyBreakdown,
    adjusted_cds_breakdown,
    adjusted_cds_spread,
    bond_cds_basis,
    bond_cds_basis_breakdown,
    cds_adjusted_risk_free_rate,
    proxy_risk_free_breakdown,
)
from .pricing import CdsPricer, CdsPricingResult
from .quotes import CdsQuote
from .reference_data import CdsReferenceData
from .instruments import Cds, CdsPremiumPeriod, CreditDefaultSwap, ProtectionSide
from .risk import cds_cs01, cs01, risky_pv01

__all__ = [
    "AdjustedCdsBreakdown",
    "BondCdsBasisBreakdown",
    "Cds",
    "CdsPremiumPeriod",
    "CdsPricer",
    "CdsPricingResult",
    "CdsQuote",
    "CdsReferenceData",
    "CreditDefaultSwap",
    "ProtectionSide",
    "RiskFreeProxyBreakdown",
    "adjusted_cds_breakdown",
    "adjusted_cds_spread",
    "bond_cds_basis",
    "bond_cds_basis_breakdown",
    "cds_adjusted_risk_free_rate",
    "cds_cs01",
    "cs01",
    "proxy_risk_free_breakdown",
    "risky_pv01",
]
