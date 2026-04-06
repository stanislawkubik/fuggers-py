"""Static reference data, conventions, metadata, and contract specs.

The reference package groups stable market descriptors used to build
instruments, resolve conventions, and normalize external data. Public docs
should treat this package as the home for identifiers, conventions, and
reference records rather than pricing logic.
"""

from __future__ import annotations

from importlib import import_module


_PACKAGE_EXPORTS = {
    "base": "fuggers_py.reference.base",
    "bonds": "fuggers_py.reference.bonds",
    "inflation": "fuggers_py.reference.inflation",
}

_SYMBOL_EXPORTS = {
    "BondType": "fuggers_py.reference.reference_data",
    "RateIndex": "fuggers_py.reference.bonds.types",
    "Tenor": "fuggers_py.reference.bonds.types",
    "YieldCalculationRules": "fuggers_py.reference.bonds.types",
    "BondFutureContractReference": "fuggers_py.reference.reference_data",
    "BondFutureReferenceData": "fuggers_py.reference.reference_data",
    "BondReferenceData": "fuggers_py.reference.reference_data",
    "BondReferenceSource": "fuggers_py.reference.reference_data",
    "CallScheduleEntry": "fuggers_py.reference.reference_data",
    "CdsReferenceData": "fuggers_py.reference.reference_data",
    "DeliverableBondReference": "fuggers_py.reference.reference_data",
    "EtfHoldingsSource": "fuggers_py.reference.reference_data",
    "FloatingRateTerms": "fuggers_py.reference.reference_data",
    "FutureReferenceData": "fuggers_py.reference.reference_data",
    "IssuerReferenceData": "fuggers_py.reference.reference_data",
    "IssuerReferenceSource": "fuggers_py.reference.reference_data",
    "IssuerType": "fuggers_py.reference.reference_data",
    "RatingRecord": "fuggers_py.reference.reference_data",
    "RatingSource": "fuggers_py.reference.reference_data",
    "ReferenceData": "fuggers_py.reference.base",
    "ReferenceDataProvider": "fuggers_py.reference.reference_data",
    "ResolvableReference": "fuggers_py.reference.base",
    "RepoReferenceData": "fuggers_py.reference.reference_data",
    "SwapReferenceData": "fuggers_py.reference.reference_data",
}

__all__ = [*_PACKAGE_EXPORTS, *_SYMBOL_EXPORTS]


def __getattr__(name: str) -> object:
    if name in _PACKAGE_EXPORTS:
        return import_module(_PACKAGE_EXPORTS[name])
    if name in _SYMBOL_EXPORTS:
        module = import_module(_SYMBOL_EXPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
