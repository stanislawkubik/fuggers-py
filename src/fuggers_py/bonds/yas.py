"""Bond YAS-style analytics for the first-layer public facade."""

from __future__ import annotations

from ._yas.analysis import BloombergReference, ValidationFailure, YASResult, YasAnalysis, YasAnalysisBuilder
from ._yas.calculator import BatchYASCalculator, YASCalculator
from ._yas.invoice import (
    SettlementInvoice,
    SettlementInvoiceBuilder,
    calculate_accrued_amount,
    calculate_proceeds,
    calculate_settlement_date,
)

__all__ = [
    "BatchYASCalculator",
    "BloombergReference",
    "SettlementInvoice",
    "SettlementInvoiceBuilder",
    "ValidationFailure",
    "YASCalculator",
    "YASResult",
    "YasAnalysis",
    "YasAnalysisBuilder",
    "calculate_accrued_amount",
    "calculate_proceeds",
    "calculate_settlement_date",
]
