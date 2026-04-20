"""Compatibility wrapper for the new first-layer bond product facade."""

from __future__ import annotations

__all__ = [
    "AccruedInterestCalculator",
    "AccruedInterestInputs",
    "AccelerationOption",
    "AmortizingBond",
    "Bond",
    "BondAnalytics",
    "BondCashFlow",
    "BondError",
    "BondPricingError",
    "CashFlowGenerator",
    "CashFlowType",
    "CallEntry",
    "CallSchedule",
    "CallType",
    "CallableBond",
    "CallableBondBuilder",
    "EmbeddedOptionBond",
    "FixedBond",
    "FixedBondBuilder",
    "FixedCouponBond",
    "FixedRateBond",
    "FixedRateBondBuilder",
    "FloatingCouponBond",
    "FloatingRateNote",
    "FloatingRateNoteBuilder",
    "IdentifierError",
    "InflationLinkedBond",
    "InvalidBondSpec",
    "InvalidIdentifier",
    "MissingRequiredField",
    "Schedule",
    "ScheduleConfig",
    "ScheduleError",
    "SettlementCalculator",
    "SettlementError",
    "SinkingFundBond",
    "SinkingFundBondBuilder",
    "SinkingFundEntry",
    "SinkingFundPayment",
    "SinkingFundSchedule",
    "TipsBond",
    "YieldConvergenceFailed",
    "ZeroCouponBond",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import fuggers_py.bonds.products as _public_module

    return getattr(_public_module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
