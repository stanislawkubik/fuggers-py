"""Public rates curve ontology.

The root package is now intentionally small. It exposes only the rates-specific
public abstractions that upstream code should build around.
"""

from .rates import CurveSpec, CurveType, ExtrapolationPolicy, RateSpace, RatesTermStructure

__all__ = [
    "CurveSpec",
    "CurveType",
    "ExtrapolationPolicy",
    "RateSpace",
    "RatesTermStructure",
]
