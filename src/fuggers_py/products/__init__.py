"""Primary product namespace for tradable contract definitions.

The package groups the concrete instrument families used by the library:
bond products, credit products, funding products, and rates products. Legacy
domain packages re-export these objects for backward compatibility, but this
namespace is the canonical home for new code.
"""

from __future__ import annotations

__all__ = ["bonds", "credit", "funding", "rates"]
