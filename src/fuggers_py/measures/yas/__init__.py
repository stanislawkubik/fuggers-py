"""YAS analytics (`fuggers_py.measures.yas`).

YAS outputs are display-oriented: yields are quoted percentages, spread
fields are basis points, and invoice amounts separate percent-of-par inputs
from currency cash amounts. The package exposes both the analyst-facing
analysis container and the settlement invoice helpers used to build YAS
reports.
"""

from __future__ import annotations

from .analysis import BloombergReference, ValidationFailure, YasAnalysis, YasAnalysisBuilder, YASResult
from .calculator import BatchYASCalculator, YASCalculator
from .invoice import (
    SettlementInvoice,
    SettlementInvoiceBuilder,
    calculate_accrued_amount,
    calculate_proceeds,
    calculate_settlement_date,
)

__all__ = [
    "YasAnalysis",
    "YasAnalysisBuilder",
    "YASResult",
    "YASCalculator",
    "BatchYASCalculator",
    "BloombergReference",
    "ValidationFailure",
    "SettlementInvoice",
    "SettlementInvoiceBuilder",
    "calculate_accrued_amount",
    "calculate_proceeds",
    "calculate_settlement_date",
]
