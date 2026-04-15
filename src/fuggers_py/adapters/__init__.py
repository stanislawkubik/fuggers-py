"""External-boundary adapters for files, storage, codecs, and transport.

This namespace exposes the concrete adapters used to load, persist, encode,
and move data across the library boundary. The public surface is intentionally
small and re-exports the file, JSON, SQLite, storage, and transport building
blocks from their implementation modules.
"""

from __future__ import annotations

from importlib import import_module


_MODULE_EXPORTS = {
    "AsyncTransport": "fuggers_py.adapters.transport",
    "AuditEntry": "fuggers_py.adapters.storage",
    "AuditStore": "fuggers_py.adapters.storage",
    "BondStore": "fuggers_py.adapters.storage",
    "CSVBondReferenceSource": "fuggers_py.adapters.file",
    "CSVEtfHoldingsSource": "fuggers_py.adapters.file",
    "CSVEtfQuoteSource": "fuggers_py.adapters.file",
    "CSVIndexFixingSource": "fuggers_py.adapters.file",
    "CSVIssuerReferenceSource": "fuggers_py.adapters.file",
    "CSVQuoteSource": "fuggers_py.adapters.file",
    "CSVRatingSource": "fuggers_py.adapters.file",
    "CacheTransport": "fuggers_py.adapters.transport",
    "Codec": "fuggers_py.adapters.transport",
    "ConfigStore": "fuggers_py.adapters.storage",
    "CurveConfig": "fuggers_py.adapters.storage",
    "CurveSnapshot": "fuggers_py.adapters.storage",
    "CurveStore": "fuggers_py.adapters.storage",
    "EmptyBondReferenceSource": "fuggers_py.adapters.file",
    "EmptyEtfHoldingsSource": "fuggers_py.adapters.file",
    "EmptyIssuerReferenceSource": "fuggers_py.adapters.file",
    "EmptyRatingSource": "fuggers_py.adapters.file",
    "InMemoryPortfolioStore": "fuggers_py.adapters.portfolio_store",
    "JSONCurveInputSource": "fuggers_py.adapters.file",
    "JsonCodec": "fuggers_py.adapters.json_codec",
    "NoOpAlertPublisher": "fuggers_py.adapters.file",
    "NoOpAnalyticsPublisher": "fuggers_py.adapters.file",
    "NoOpEtfPublisher": "fuggers_py.adapters.file",
    "NoOpQuotePublisher": "fuggers_py.adapters.file",
    "OverrideRecord": "fuggers_py.adapters.storage",
    "OverrideStore": "fuggers_py.adapters.storage",
    "Page": "fuggers_py.adapters.storage",
    "Pagination": "fuggers_py.adapters.storage",
    "PortfolioFilter": "fuggers_py.adapters.storage",
    "PortfolioStore": "fuggers_py.adapters.storage",
    "PrettyJsonCodec": "fuggers_py.adapters.json_codec",
    "PricingConfig": "fuggers_py.adapters.storage",
    "RemoteStorageTransport": "fuggers_py.adapters.transport",
    "SQLiteStorageAdapter": "fuggers_py.adapters.sqlite_storage",
    "StorageAdapter": "fuggers_py.adapters.storage",
    "StoredPortfolio": "fuggers_py.adapters.storage",
    "StoredPosition": "fuggers_py.adapters.storage",
    "Transport": "fuggers_py.adapters.transport",
    "create_empty_output": "fuggers_py.adapters.file",
    "create_file_market_data": "fuggers_py.adapters.file",
    "create_file_reference_data": "fuggers_py.adapters.file",
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
