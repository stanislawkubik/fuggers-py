"""Shared market-state value objects.

These records capture the live curves, quote-side selection, and other market
state consumed by pricers and measures without pulling calc-layer orchestration
into the market package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QuoteSide(str, Enum):
    """Canonical quote-side selector used across market records."""

    BID = "bid"
    ASK = "ask"
    MID = "mid"


@dataclass(frozen=True, slots=True)
class AnalyticsCurves:
    """Container for the curve roles used by analytics and pricing flows.

    The container keeps role-based access explicit so callers can distinguish
    discount, projection, repo, inflation, and volatility inputs without
    relying on positional arguments or implicit fallbacks.
    """

    discount_curve: object | None = None
    forward_curve: object | None = None
    government_curve: object | None = None
    benchmark_curve: object | None = None
    credit_curve: object | None = None
    repo_curve: object | None = None
    collateral_curve: object | None = None
    fx_forward_curve: object | None = None
    multicurve_environment: object | None = None
    projection_curves: dict[str, object] = field(default_factory=dict)
    inflation_curve: object | None = None
    inflation_curves: dict[str, object] = field(default_factory=dict)
    vol_surface: object | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "projection_curves", {str(key): value for key, value in self.projection_curves.items()})
        object.__setattr__(self, "inflation_curves", {str(key): value for key, value in self.inflation_curves.items()})

    def get(self, role: str) -> object | None:
        """Resolve a curve by canonical role name or projection alias.

        The lookup accepts the named top-level roles defined on the container
        plus ``projection:<name>`` and ``inflation:<name>`` aliases for keyed
        sub-curves.
        """
        normalized_role = role.strip().lower()
        resolved = {
            "discount": self.discount_curve,
            "discount_curve": self.discount_curve,
            "forward": self.forward_curve,
            "forward_curve": self.forward_curve,
            "government": self.government_curve,
            "government_curve": self.government_curve,
            "benchmark": self.benchmark_curve,
            "benchmark_curve": self.benchmark_curve,
            "credit": self.credit_curve,
            "credit_curve": self.credit_curve,
            "repo": self.repo_curve,
            "repo_curve": self.repo_curve,
            "collateral": self.collateral_curve,
            "collateral_curve": self.collateral_curve,
            "fx_forward": self.fx_forward_curve,
            "fx_forward_curve": self.fx_forward_curve,
            "multicurve_environment": self.multicurve_environment,
            "inflation": self.inflation_curve,
            "inflation_curve": self.inflation_curve,
            "inflation_curves": self.inflation_curves,
            "projection_curves": self.projection_curves,
            "vol_surface": self.vol_surface,
        }.get(normalized_role)
        if resolved is not None:
            return resolved
        if normalized_role.startswith("inflation:"):
            inflation_key = role.split(":", 1)[1].strip()
            if inflation_key in self.inflation_curves:
                return self.inflation_curves[inflation_key]
            lowered = inflation_key.lower()
            for key, value in self.inflation_curves.items():
                if key.lower() == lowered:
                    return value
            return None
        if normalized_role.startswith("projection:"):
            projection_key = role.split(":", 1)[1].strip()
            if projection_key in self.projection_curves:
                return self.projection_curves[projection_key]
            lowered = projection_key.lower()
            for key, value in self.projection_curves.items():
                if key.lower() == lowered:
                    return value
            return None
        if role in self.inflation_curves:
            return self.inflation_curves[role]
        if role in self.projection_curves:
            return self.projection_curves[role]
        return None


__all__ = ["AnalyticsCurves", "QuoteSide"]
