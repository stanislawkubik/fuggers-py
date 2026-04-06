"""Public market package entrypoints.

The canonical market layout lives in submodules:

- ``fuggers_py.market.state``
- ``fuggers_py.market.quotes``
- ``fuggers_py.market.snapshot``
- ``fuggers_py.market.sources``
- ``fuggers_py.market.vol_surfaces``
- ``fuggers_py.market.curves``
- ``fuggers_py.market.indices``
"""

from __future__ import annotations

from importlib import import_module


_PACKAGE_EXPORTS = {
    "curves": "fuggers_py.market.curves",
    "indices": "fuggers_py.market.indices",
    "state": "fuggers_py.market.state",
    "quotes": "fuggers_py.market.quotes",
    "snapshot": "fuggers_py.market.snapshot",
    "sources": "fuggers_py.market.sources",
    "vol_surfaces": "fuggers_py.market.vol_surfaces",
}

__all__ = [*_PACKAGE_EXPORTS]


def __getattr__(name: str) -> object:
    if name in _PACKAGE_EXPORTS:
        return import_module(_PACKAGE_EXPORTS[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
