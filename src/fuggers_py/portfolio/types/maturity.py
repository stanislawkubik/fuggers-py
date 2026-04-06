"""Maturity bucketing compatibility types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MaturityBucket:
    """A half-open maturity bucket measured in years."""

    label: str
    start_years: float
    end_years: float | None

    def contains(self, years_to_maturity: float) -> bool:
        """Return ``True`` when ``years_to_maturity`` falls inside the bucket."""

        if years_to_maturity < self.start_years:
            return False
        if self.end_years is None:
            return True
        return years_to_maturity < self.end_years


__all__ = ["MaturityBucket"]
