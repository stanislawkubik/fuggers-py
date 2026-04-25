"""YAS analysis containers (`fuggers_py.bonds._yas.analysis`).

The analysis object stores display-oriented yield and spread fields together
with the computed risk bundle and settlement invoice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py._core import Tenor

from ..risk import BondRiskMetrics
from .invoice import SettlementInvoice


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    """Bloomberg validation mismatch for a single field."""

    field: str
    expected: Decimal
    actual: Decimal
    tolerance: Decimal


@dataclass(frozen=True, slots=True)
class BloombergReference:
    """Reference values used by the Bloomberg validation helper."""

    ytm: Decimal
    g_spread_bps: Decimal
    z_spread_bps: Decimal
    modified_duration: Decimal
    convexity: Decimal

    @classmethod
    def boeing_2025(cls) -> "BloombergReference":
        """Return the Boeing 2025 reference values used by the tests."""

        return cls(
            ytm=_to_decimal("4.905895"),
            g_spread_bps=_to_decimal("448.5"),
            z_spread_bps=_to_decimal("444.7"),
            modified_duration=_to_decimal("4.209"),
            convexity=_to_decimal("0.219"),
        )


@dataclass(frozen=True, slots=True)
class YasAnalysis:
    """Display-oriented YAS output bundle.

    Yields are quoted percentages. Spread fields are in basis points. The
    attached invoice separates clean-price inputs from currency cash amounts.
    """

    ytm: Decimal
    street_yield: Decimal
    true_yield: Decimal
    current_yield: Decimal
    simple_yield: Decimal
    money_market_yield: Decimal | None
    g_spread_bps: Decimal | None
    z_spread_bps: Decimal | None
    benchmark_spread_bps: Decimal | None
    benchmark_tenor: Tenor | None
    risk: BondRiskMetrics
    invoice: SettlementInvoice

    def modified_duration(self) -> Decimal:
        """Return the modified duration from the attached risk bundle."""

        return self.risk.modified_duration

    def convexity(self) -> Decimal:
        """Return the convexity from the attached risk bundle."""

        return self.risk.convexity

    def dv01(self) -> Decimal:
        """Return the DV01 from the attached risk bundle."""

        return self.risk.dv01


@dataclass(slots=True)
class YasAnalysisBuilder:
    """Builder for :class:`YasAnalysis` instances."""

    ytm: Decimal | None = None
    street_yield: Decimal | None = None
    true_yield: Decimal | None = None
    current_yield: Decimal | None = None
    simple_yield: Decimal | None = None
    money_market_yield: Decimal | None = None
    g_spread_bps: Decimal | None = None
    z_spread_bps: Decimal | None = None
    benchmark_spread_bps: Decimal | None = None
    benchmark_tenor: Tenor | None = None
    risk: BondRiskMetrics | None = None
    invoice: SettlementInvoice | None = None

    def build(self) -> YasAnalysis:
        """Validate required fields and build a :class:`YasAnalysis`."""

        if self.ytm is None or self.street_yield is None or self.true_yield is None:
            raise ValueError("YAS analysis requires ytm, street_yield, and true_yield.")
        if self.current_yield is None or self.simple_yield is None:
            raise ValueError("YAS analysis requires current_yield and simple_yield.")
        if self.risk is None or self.invoice is None:
            raise ValueError("YAS analysis requires risk metrics and invoice.")
        return YasAnalysis(
            ytm=self.ytm,
            street_yield=self.street_yield,
            true_yield=self.true_yield,
            current_yield=self.current_yield,
            simple_yield=self.simple_yield,
            money_market_yield=self.money_market_yield,
            g_spread_bps=self.g_spread_bps,
            z_spread_bps=self.z_spread_bps,
            benchmark_spread_bps=self.benchmark_spread_bps,
            benchmark_tenor=self.benchmark_tenor,
            risk=self.risk,
            invoice=self.invoice,
        )


YASResult = YasAnalysis


__all__ = [
    "YasAnalysis",
    "YasAnalysisBuilder",
    "YASResult",
    "BloombergReference",
    "ValidationFailure",
]
