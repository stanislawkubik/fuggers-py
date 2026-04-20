"""ETF SEC/distribution yield helpers.

The SEC-yield helpers keep the distinction between standardized SEC yield,
approximate historical yield, and distribution yield expressed in raw decimal,
percent, and basis-point forms.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import overload
import warnings

from fuggers_py._core import Date

from ..analytics import PortfolioAnalytics
from ..portfolio import Portfolio
from ..results import DistributionYield


@dataclass(frozen=True, slots=True)
class SecYieldInput:
    """Inputs for the standardized SEC-yield calculation."""

    net_investment_income: Decimal
    average_shares_outstanding: Decimal
    max_offering_price: Decimal
    gross_expenses: Decimal | None = None
    fee_waivers: Decimal | None = None
    as_of_date: Date | None = None


@dataclass(frozen=True, slots=True)
class SecYield:
    """Standardized SEC yield output and related inputs."""

    sec_30_day_yield: Decimal
    unsubsidized_yield: Decimal | None
    net_investment_income: Decimal
    average_shares_outstanding: Decimal
    max_offering_price: Decimal
    gross_expenses: Decimal | None = None
    fee_waivers: Decimal | None = None
    as_of_date: Date | None = None

    def fee_waiver_impact(self) -> Decimal | None:
        """Return the yield impact of fee waivers when available."""

        return None if self.unsubsidized_yield is None else self.sec_30_day_yield - self.unsubsidized_yield


@dataclass(frozen=True, slots=True)
class ExpenseMetrics:
    """Yield and expense metrics estimated from holdings."""

    gross_yield: Decimal
    net_yield: Decimal
    gross_expense_ratio: Decimal
    net_expense_ratio: Decimal
    fee_waiver_ratio: Decimal
    annual_income_estimate: Decimal
    annual_expense_amount: Decimal
    net_assets: Decimal

    @property
    def expense_drag(self) -> Decimal:
        """Return the yield drag from expenses."""

        return self.gross_yield - self.net_yield

    @property
    def yield_before_expenses(self) -> Decimal:
        """Return the gross yield."""

        return self.gross_yield

    @property
    def yield_after_expenses(self) -> Decimal:
        """Return the net yield."""

        return self.net_yield


class ComplianceSeverity(str, Enum):
    """Severity of an ETF compliance check."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class ComplianceCheck:
    """Single ETF compliance check result."""

    name: str
    passed: bool
    value: Decimal
    limit: Decimal
    description: str
    severity: ComplianceSeverity


@dataclass(frozen=True, slots=True)
class EtfComplianceReport:
    """Summary of ETF compliance checks."""

    weights_sum_to_one: bool
    issuer_limit_ok: bool
    checks: tuple[ComplianceCheck, ...]

    @property
    def passed(self) -> bool:
        """Return ``True`` when all checks pass."""

        return all(check.passed for check in self.checks)

    def by_name(self, name: str) -> ComplianceCheck | None:
        """Return the named compliance check if present."""

        for check in self.checks:
            if check.name == name:
                return check
        return None


def _annualize_sec_yield(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        raise ValueError("SEC-yield denominator must be positive.")
    ratio = numerator / denominator
    return Decimal(2) * (((Decimal(1) + ratio) ** 6) - Decimal(1))


def approximate_sec_yield(net_investment_income: Decimal, net_assets: Decimal) -> Decimal:
    """Return the historical SEC-yield approximation as a raw decimal."""

    if net_assets <= 0:
        raise ValueError("net_assets must be positive.")
    return net_investment_income / net_assets * Decimal(2)


@overload
def calculate_sec_yield(input_data: SecYieldInput, net_assets: None = None) -> SecYield:
    """Return the standardized SEC-yield record."""

    ...


@overload
def calculate_sec_yield(net_investment_income: Decimal, net_assets: Decimal) -> Decimal:
    """Return the legacy approximate SEC yield."""

    ...


def calculate_sec_yield(
    input_data: SecYieldInput | Decimal,
    net_assets: Decimal | None = None,
) -> SecYield | Decimal:
    """Return either standardized SEC yield or the legacy approximation."""

    if isinstance(input_data, SecYieldInput):
        if input_data.average_shares_outstanding <= 0:
            raise ValueError("average_shares_outstanding must be positive.")
        if input_data.max_offering_price <= 0:
            raise ValueError("max_offering_price must be positive.")
        denominator = input_data.average_shares_outstanding * input_data.max_offering_price
        unsubsidized = None
        if input_data.fee_waivers is not None:
            unsubsidized = _annualize_sec_yield(input_data.net_investment_income - input_data.fee_waivers, denominator)
        return SecYield(
            sec_30_day_yield=_annualize_sec_yield(input_data.net_investment_income, denominator),
            unsubsidized_yield=unsubsidized,
            net_investment_income=input_data.net_investment_income,
            average_shares_outstanding=input_data.average_shares_outstanding,
            max_offering_price=input_data.max_offering_price,
            gross_expenses=input_data.gross_expenses,
            fee_waivers=input_data.fee_waivers,
            as_of_date=input_data.as_of_date,
        )

    if net_assets is None:
        raise TypeError("Legacy calculate_sec_yield calls require both net_investment_income and net_assets.")
    warnings.warn(
        "calculate_sec_yield(net_investment_income, net_assets) is deprecated; use "
        "calculate_sec_yield(SecYieldInput(...)) for standardized SEC-yield output or "
        "approximate_sec_yield(...) for the historical approximation.",
        DeprecationWarning,
        stacklevel=2,
    )
    return approximate_sec_yield(input_data, net_assets)


def calculate_distribution_yield(annual_distribution: Decimal, market_price: Decimal) -> DistributionYield:
    """Return distribution yield as decimal, percent, and basis points."""

    if market_price <= 0:
        raise ValueError("market_price must be positive.")
    distribution_yield = annual_distribution / market_price
    return DistributionYield(
        distribution_yield=distribution_yield,
        annual_distribution=annual_distribution,
        market_price=market_price,
        distribution_yield_pct=distribution_yield * Decimal(100),
        distribution_yield_bps=distribution_yield * Decimal(10_000),
    )


def estimate_yield_from_holdings(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    gross_expense_ratio: Decimal = Decimal(0),
    fee_waiver_ratio: Decimal = Decimal(0),
) -> ExpenseMetrics:
    """Estimate gross and net yield after expenses from holdings.

    The gross yield is based on the portfolio YTM, then adjusted by the input
    expense and fee-waiver ratios to produce a net-yield estimate.
    """

    gross_ratio = Decimal(str(gross_expense_ratio))
    waiver_ratio = Decimal(str(fee_waiver_ratio))
    if gross_ratio < 0:
        raise ValueError("gross_expense_ratio must be non-negative.")
    if waiver_ratio < 0:
        raise ValueError("fee_waiver_ratio must be non-negative.")
    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    net_expense_ratio = gross_ratio - waiver_ratio
    if net_expense_ratio < 0:
        net_expense_ratio = Decimal(0)
    gross_yield = metrics.ytm
    net_assets = metrics.dirty_pv
    annual_income = gross_yield * net_assets
    annual_expenses = net_expense_ratio * net_assets
    return ExpenseMetrics(
        gross_yield=gross_yield,
        net_yield=gross_yield - net_expense_ratio,
        gross_expense_ratio=gross_ratio,
        net_expense_ratio=net_expense_ratio,
        fee_waiver_ratio=waiver_ratio,
        annual_income_estimate=annual_income,
        annual_expense_amount=annual_expenses,
        net_assets=net_assets,
    )


def etf_compliance_checks(*, holdings_weight_sum: Decimal, max_issuer_weight: Decimal | None = None) -> EtfComplianceReport:
    """Evaluate a small set of ETF compliance checks.

    The checks are intentionally simple: holdings weights should sum to one,
    and the issuer limit must stay within the provided bound when supplied.
    """

    if max_issuer_weight is not None and max_issuer_weight < 0:
        raise ValueError("max_issuer_weight must be non-negative.")

    weights_diff = abs(holdings_weight_sum - Decimal(1))
    weights_sum_to_one = weights_diff <= Decimal("0.0001")
    if weights_sum_to_one:
        weights_severity = ComplianceSeverity.INFO
    elif weights_diff <= Decimal("0.01"):
        weights_severity = ComplianceSeverity.WARNING
    else:
        weights_severity = ComplianceSeverity.CRITICAL

    issuer_limit = Decimal("0.25")
    issuer_limit_ok = True if max_issuer_weight is None else max_issuer_weight <= issuer_limit
    if max_issuer_weight is None or issuer_limit_ok:
        issuer_severity = ComplianceSeverity.INFO
        issuer_value = Decimal(0) if max_issuer_weight is None else max_issuer_weight
    elif max_issuer_weight <= issuer_limit * Decimal("1.1"):
        issuer_severity = ComplianceSeverity.WARNING
        issuer_value = max_issuer_weight
    else:
        issuer_severity = ComplianceSeverity.CRITICAL
        issuer_value = max_issuer_weight

    checks = (
        ComplianceCheck(
            name="weights_sum_to_one",
            passed=weights_sum_to_one,
            value=holdings_weight_sum,
            limit=Decimal(1),
            description="Holdings weights should sum to one within a small tolerance.",
            severity=weights_severity,
        ),
        ComplianceCheck(
            name="issuer_limit_ok",
            passed=issuer_limit_ok,
            value=issuer_value,
            limit=issuer_limit,
            description="Largest issuer weight should remain within the configured 25% limit.",
            severity=issuer_severity,
        ),
    )
    return EtfComplianceReport(
        weights_sum_to_one=weights_sum_to_one,
        issuer_limit_ok=issuer_limit_ok,
        checks=checks,
    )


__all__ = [
    "ComplianceCheck",
    "ComplianceSeverity",
    "DistributionYield",
    "ExpenseMetrics",
    "EtfComplianceReport",
    "SecYield",
    "SecYieldInput",
    "approximate_sec_yield",
    "calculate_distribution_yield",
    "calculate_sec_yield",
    "etf_compliance_checks",
    "estimate_yield_from_holdings",
]
