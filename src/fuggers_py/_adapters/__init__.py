"""External-boundary adapters for file-backed edge helpers.

This namespace now keeps only the file-backed helpers that still sit at the
edge of the public library story. Storage, JSON, SQLite, transport, and
portfolio-store helpers have moved to the internal ``_storage`` package.
"""

from __future__ import annotations

from importlib import import_module


_MODULE_EXPORTS = {
    "CSVBondReferenceSource": "fuggers_py._adapters.file",
    "CSVEtfHoldingsSource": "fuggers_py._adapters.file",
    "CSVEtfQuoteSource": "fuggers_py._adapters.file",
    "CSVIndexFixingSource": "fuggers_py._adapters.file",
    "CSVIssuerReferenceSource": "fuggers_py._adapters.file",
    "CSVQuoteSource": "fuggers_py._adapters.file",
    "CSVRatingSource": "fuggers_py._adapters.file",
    "EmptyBondReferenceSource": "fuggers_py._adapters.file",
    "EmptyEtfHoldingsSource": "fuggers_py._adapters.file",
    "EmptyIssuerReferenceSource": "fuggers_py._adapters.file",
    "EmptyRatingSource": "fuggers_py._adapters.file",
    "JSONCurveInputSource": "fuggers_py._adapters.file",
    "NoOpAlertPublisher": "fuggers_py._adapters.file",
    "NoOpAnalyticsPublisher": "fuggers_py._adapters.file",
    "NoOpEtfPublisher": "fuggers_py._adapters.file",
    "NoOpQuotePublisher": "fuggers_py._adapters.file",
    "create_empty_output": "fuggers_py._adapters.file",
    "create_file_market_data": "fuggers_py._adapters.file",
    "create_file_reference_data": "fuggers_py._adapters.file",
}

__all__ = list(_MODULE_EXPORTS)


def __getattr__(name: str) -> object:
    module_name = _MODULE_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
