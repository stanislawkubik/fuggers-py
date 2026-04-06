"""Seniority compatibility types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Seniority(str, Enum):
    """Issuer seniority classification."""

    SOVEREIGN = "SOVEREIGN"
    SENIOR_SECURED = "SENIOR_SECURED"
    SENIOR_UNSECURED = "SENIOR_UNSECURED"
    SUBORDINATED = "SUBORDINATED"
    JUNIOR_SUBORDINATED = "JUNIOR_SUBORDINATED"
    PREFERRED = "PREFERRED"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class SeniorityInfo:
    """Seniority metadata attached to a bond or issuer."""

    seniority: Seniority
    secured: bool = False


__all__ = ["Seniority", "SeniorityInfo"]
