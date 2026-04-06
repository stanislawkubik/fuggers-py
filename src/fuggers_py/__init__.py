"""Public package roots for the :mod:`fuggers_py` fixed-income library.

The top-level package exposes the responsibility-first subpackages used across
the library: core primitives, reference data, market state, product
definitions, pricers, user-facing measures, portfolio analytics, calculation
orchestration, adapters, and numerical helpers.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as distribution_version

try:
    from ._version import version as __version__
except ImportError:
    try:
        __version__ = distribution_version("fuggers-py")
    except PackageNotFoundError:
        __version__ = "0.0.dev0"

__all__ = [
    "__version__",
    "adapters",
    "calc",
    "core",
    "market",
    "math",
    "measures",
    "portfolio",
    "pricers",
    "products",
    "reference",
]
