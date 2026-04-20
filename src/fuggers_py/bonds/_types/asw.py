"""Shared asset-swap enum types."""

from __future__ import annotations

from enum import Enum


class ASWType(str, Enum):
    """Asset-swap quote convention."""

    PAR_PAR = "PAR_PAR"
    PROCEEDS = "PROCEEDS"


__all__ = ["ASWType"]
