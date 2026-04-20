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
from .products import Cds, CdsPremiumPeriod, CreditDefaultSwap, ProtectionSide
from .quotes import CdsQuote

__all__ = [
    "AdjustedCdsBreakdown",
    "BondCdsBasisBreakdown",
    "Cds",
    "CdsPremiumPeriod",
    "CdsPricer",
    "CdsPricingResult",
    "CdsQuote",
    "CreditDefaultSwap",
    "ProtectionSide",
    "RiskFreeProxyBreakdown",
    "adjusted_cds_breakdown",
    "adjusted_cds_spread",
    "bond_cds_basis",
    "bond_cds_basis_breakdown",
    "cds_adjusted_risk_free_rate",
    "proxy_risk_free_breakdown",
]
