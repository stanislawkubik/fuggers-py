"""Error hierarchy for bond-option models and tree pricing helpers."""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.errors import FuggersError


@dataclass(frozen=True, slots=True)
class ModelError(FuggersError):
    """Raised when a short-rate model or bond-option input is invalid."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Model error: {self.reason}"


__all__ = ["ModelError"]
