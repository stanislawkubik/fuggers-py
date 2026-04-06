from __future__ import annotations

from fuggers_py.calc import CdsQuoteOutput, RvSignalOutput
from fuggers_py.market.quotes import CdsQuote
from fuggers_py.market.curves.credit import (
    CdsBootstrapPoint,
    CdsBootstrapResult,
    bootstrap_credit_curve,
)
from fuggers_py.measures.credit import (
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
from fuggers_py.pricers.credit import CdsPricer, CdsPricingResult
from fuggers_py.products.credit import Cds, CreditDefaultSwap, ProtectionSide
from fuggers_py.reference import CdsReferenceData
from fuggers_py.measures.credit import AdjustedCdsBreakdown as analytics_adjusted_cds_breakdown_type
from fuggers_py.measures.credit import BondCdsBasisBreakdown as analytics_bond_cds_basis_breakdown_type
from fuggers_py.measures.credit import RiskFreeProxyBreakdown as analytics_risk_free_proxy_breakdown_type
from fuggers_py.measures.credit import adjusted_cds_breakdown as analytics_adjusted_cds_breakdown
from fuggers_py.measures.credit import adjusted_cds_spread as analytics_adjusted_cds_spread
from fuggers_py.measures.credit import bond_cds_basis as analytics_bond_cds_basis
from fuggers_py.measures.credit import bond_cds_basis_breakdown as analytics_bond_cds_basis_breakdown
from fuggers_py.measures.credit import cds_adjusted_risk_free_rate as analytics_cds_adjusted_risk_free_rate
from fuggers_py.measures.credit import proxy_risk_free_breakdown as analytics_proxy_risk_free_breakdown
from fuggers_py.market.curves.credit import CdsBootstrapPoint as curves_cds_bootstrap_point
from fuggers_py.market.curves.credit import CdsBootstrapResult as curves_cds_bootstrap_result
from fuggers_py.market.curves.credit import bootstrap_credit_curve as curves_bootstrap_credit_curve
from fuggers_py.products.credit import Cds as instruments_cds
from fuggers_py.products.credit import CreditDefaultSwap as instruments_credit_default_swap
from fuggers_py.products.credit import ProtectionSide as instruments_protection_side
from fuggers_py.pricers.credit import CdsPricer as pricing_cds_pricer
from fuggers_py.pricers.credit import CdsPricingResult as pricing_cds_pricing_result
from fuggers_py.market.quotes import CdsQuote as data_cds_quote
from fuggers_py.calc import CdsQuoteOutput as data_cds_quote_output
from fuggers_py.reference import CdsReferenceData as data_cds_reference_data
from fuggers_py.calc import RvSignalOutput as data_rv_signal_output


def test_credit_root_exports_scaffold_records() -> None:
    assert CdsQuote is data_cds_quote
    assert CdsQuoteOutput is data_cds_quote_output
    assert CdsReferenceData is data_cds_reference_data
    assert RvSignalOutput is data_rv_signal_output
    assert Cds is instruments_cds
    assert CreditDefaultSwap is instruments_credit_default_swap
    assert ProtectionSide is instruments_protection_side
    assert CdsPricer is pricing_cds_pricer
    assert CdsPricingResult is pricing_cds_pricing_result
    assert CdsBootstrapPoint is curves_cds_bootstrap_point
    assert CdsBootstrapResult is curves_cds_bootstrap_result
    assert bootstrap_credit_curve is curves_bootstrap_credit_curve
    assert AdjustedCdsBreakdown is analytics_adjusted_cds_breakdown_type
    assert adjusted_cds_breakdown is analytics_adjusted_cds_breakdown
    assert adjusted_cds_spread is analytics_adjusted_cds_spread
    assert BondCdsBasisBreakdown is analytics_bond_cds_basis_breakdown_type
    assert bond_cds_basis is analytics_bond_cds_basis
    assert bond_cds_basis_breakdown is analytics_bond_cds_basis_breakdown
    assert RiskFreeProxyBreakdown is analytics_risk_free_proxy_breakdown_type
    assert cds_adjusted_risk_free_rate is analytics_cds_adjusted_risk_free_rate
    assert proxy_risk_free_breakdown is analytics_proxy_risk_free_breakdown
