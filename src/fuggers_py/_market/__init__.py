"""Public market package entrypoints.

The public market namespace owns:

- ``fuggers_py._market.state``
- ``fuggers_py._market.snapshot``
- ``fuggers_py._market.sources``
- ``fuggers_py._market.indices``

Fitted curves and volatility surfaces now have first-layer public homes under
``fuggers_py.curves`` and ``fuggers_py.vol_surfaces``.
"""

from __future__ import annotations

from importlib import import_module


_PACKAGE_EXPORTS = {
    "indices": "fuggers_py._market.indices",
    "state": "fuggers_py._market.state",
    "snapshot": "fuggers_py._market.snapshot",
    "sources": "fuggers_py._market.sources",
}

__all__ = [*_PACKAGE_EXPORTS]


def __getattr__(name: str) -> object:
    if name in _PACKAGE_EXPORTS:
        return import_module(_PACKAGE_EXPORTS[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
