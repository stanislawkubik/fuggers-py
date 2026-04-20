"""Compatibility wrapper for the new first-layer bond pricing facade."""

from __future__ import annotations

__all__ = [
    "BondPricer",
    "BondResult",
    "CashFlowData",
    "DurationResult",
    "PriceResult",
    "RiskMetrics",
    "StandardYieldEngine",
    "TipsPricer",
    "YieldEngineResult",
    "YieldResult",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import fuggers_py.bonds.pricing as _public_module

    return getattr(_public_module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
