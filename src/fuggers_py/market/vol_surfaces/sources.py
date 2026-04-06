"""Volatility surface source protocols and in-memory providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from fuggers_py.core.ids import VolSurfaceId

from .surface import VolatilitySurface


@runtime_checkable
class VolatilitySource(Protocol):
    """Protocol for retrieving volatility surfaces."""

    def get_volatility_surface(self, surface_id: VolSurfaceId | str) -> VolatilitySurface | None:
        ...


@dataclass(slots=True)
class InMemoryVolatilitySource:
    """Deterministic in-memory volatility surface source."""

    surfaces: dict[VolSurfaceId, VolatilitySurface] = field(default_factory=dict)

    def __init__(self, surfaces: tuple[VolatilitySurface, ...] | list[VolatilitySurface] | None = None) -> None:
        self.surfaces = {}
        for surface in surfaces or ():
            self.add_surface(surface)

    def add_surface(self, surface: VolatilitySurface) -> "InMemoryVolatilitySource":
        """Store a volatility surface keyed by its normalized identifier."""
        self.surfaces[surface.surface_id] = surface
        return self

    def get_volatility_surface(self, surface_id: VolSurfaceId | str) -> VolatilitySurface | None:
        """Return the requested volatility surface when present."""
        resolved = surface_id if isinstance(surface_id, VolSurfaceId) else VolSurfaceId.parse(surface_id)
        return self.surfaces.get(resolved)


__all__ = [
    "InMemoryVolatilitySource",
    "VolatilitySource",
]
