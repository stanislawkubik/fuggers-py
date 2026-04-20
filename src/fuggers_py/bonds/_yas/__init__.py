"""Compatibility wrapper for the new first-layer bond YAS facade."""

from __future__ import annotations

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


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import fuggers_py.bonds.yas as _public_module

    return getattr(_public_module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
