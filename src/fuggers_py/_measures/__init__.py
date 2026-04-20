"""Internal analytics, desk measures, and report-oriented helpers."""

from __future__ import annotations

from importlib import import_module


_SUBMODULE_EXPORTS = {
    "cashflows": "fuggers_py._measures.cashflows",
    "options": "fuggers_py._measures.options",
    "pricing": "fuggers_py._measures.pricing",
    "risk": "fuggers_py._measures.risk",
    "rv": "fuggers_py._measures.rv",
    "spreads": "fuggers_py._measures.spreads",
    "yas": "fuggers_py._measures.yas",
    "yields": "fuggers_py._measures.yields",
}

_VALUE_EXPORTS = {
    "AnalyticsError": "fuggers_py._measures.errors",
    "current_yield": "fuggers_py._measures.yields",
    "current_yield_pct": "fuggers_py._measures.yields",
    "simple_yield": "fuggers_py._measures.yields",
    "yield_to_maturity": "fuggers_py._measures.functions",
}

__all__ = [
    "cashflows",
    "options",
    "pricing",
    "risk",
    "rv",
    "spreads",
    "yas",
    "yields",
    "AnalyticsError",
    "current_yield",
    "current_yield_pct",
    "simple_yield",
    "yield_to_maturity",
]


def __getattr__(name: str) -> object:
    module_name = _SUBMODULE_EXPORTS.get(name)
    if module_name is not None:
        module = import_module(module_name)
        globals()[name] = module
        return module

    module_name = _VALUE_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
