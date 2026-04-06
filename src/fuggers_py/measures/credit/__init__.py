"""Credit desk analytics and named measures.

The public surface includes CDS adjustment helpers, bond-versus-CDS basis
decomposition, and CDS-adjusted proxy risk-free rate calculations. Spreads are
expressed as raw decimals unless a helper explicitly returns a quoted display
format.
"""

from __future__ import annotations

from .adjusted_cds import AdjustedCdsBreakdown, adjusted_cds_breakdown, adjusted_cds_spread
from .bond_cds_basis import BondCdsBasisBreakdown, bond_cds_basis, bond_cds_basis_breakdown
from .risk_free_proxy import RiskFreeProxyBreakdown, cds_adjusted_risk_free_rate, proxy_risk_free_breakdown

__all__ = [
    "AdjustedCdsBreakdown",
    "BondCdsBasisBreakdown",
    "RiskFreeProxyBreakdown",
    "adjusted_cds_breakdown",
    "adjusted_cds_spread",
    "bond_cds_basis",
    "bond_cds_basis_breakdown",
    "cds_adjusted_risk_free_rate",
    "proxy_risk_free_breakdown",
]
