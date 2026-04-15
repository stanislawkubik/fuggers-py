"""User-facing analytics, desk measures, and report-oriented helpers.

The package groups the public analytics surface into yield, spread, risk,
relative-value, options, credit, funding, cashflow, and YAS subpackages. Raw
decimal units are used for rates and spreads unless a helper explicitly says
otherwise.

The top-level convenience entry points are the broad bond analytics helpers in
``functions`` plus the simple yield helpers re-exported here. More specialized
workflows live in the named subpackages such as ``risk``, ``spreads``, ``rv``,
``funding``, ``yas``, and ``yields``.
"""

from __future__ import annotations

from importlib import import_module


_SUBMODULE_EXPORTS = {
    "cashflows": "fuggers_py.measures.cashflows",
    "credit": "fuggers_py.measures.credit",
    "funding": "fuggers_py.measures.funding",
    "options": "fuggers_py.measures.options",
    "pricing": "fuggers_py.measures.pricing",
    "risk": "fuggers_py.measures.risk",
    "rv": "fuggers_py.measures.rv",
    "spreads": "fuggers_py.measures.spreads",
    "yas": "fuggers_py.measures.yas",
    "yields": "fuggers_py.measures.yields",
}

_VALUE_EXPORTS = {
    "AnalyticsError": "fuggers_py.measures.errors",
    "current_yield": "fuggers_py.measures.yields",
    "current_yield_pct": "fuggers_py.measures.yields",
    "simple_yield": "fuggers_py.measures.yields",
    "yield_to_maturity": "fuggers_py.measures.functions",
}

__all__ = [
    "cashflows",
    "credit",
    "funding",
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
