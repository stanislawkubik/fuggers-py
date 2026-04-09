"""Internal helpers for legacy curve semantics."""

from __future__ import annotations

from .value_type import ValueType


def stored_value_type(curve: object) -> ValueType:
    value = getattr(curve, "_value_type", None)
    if value is None:
        raise AttributeError(f"{type(curve).__name__} does not carry internal curve value semantics.")
    return value


__all__ = ["stored_value_type"]
