"""Internal storage and boundary helpers."""

from __future__ import annotations

from importlib import import_module


_MODULE_EXPORTS = {
    "AsyncTransport": "fuggers_py._storage.transport",
    "AuditEntry": "fuggers_py._storage.storage",
    "AuditStore": "fuggers_py._storage.storage",
    "BondStore": "fuggers_py._storage.storage",
    "CacheTransport": "fuggers_py._storage.transport",
    "Codec": "fuggers_py._storage.transport",
    "ConfigStore": "fuggers_py._storage.storage",
    "CurveConfig": "fuggers_py._storage.storage",
    "CurveSnapshot": "fuggers_py._storage.storage",
    "CurveStore": "fuggers_py._storage.storage",
    "InMemoryPortfolioStore": "fuggers_py._storage.portfolio_store",
    "JsonCodec": "fuggers_py._storage.json_codec",
    "OverrideRecord": "fuggers_py._storage.storage",
    "OverrideStore": "fuggers_py._storage.storage",
    "Page": "fuggers_py._storage.storage",
    "Pagination": "fuggers_py._storage.storage",
    "PortfolioFilter": "fuggers_py._storage.storage",
    "PortfolioStore": "fuggers_py._storage.storage",
    "PrettyJsonCodec": "fuggers_py._storage.json_codec",
    "PricingConfig": "fuggers_py._storage.storage",
    "RemoteStorageTransport": "fuggers_py._storage.transport",
    "SQLiteStorageAdapter": "fuggers_py._storage.sqlite_storage",
    "StorageAdapter": "fuggers_py._storage.storage",
    "StoredPortfolio": "fuggers_py._storage.storage",
    "StoredPosition": "fuggers_py._storage.storage",
    "Transport": "fuggers_py._storage.transport",
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
