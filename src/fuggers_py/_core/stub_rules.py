"""Shared stub-period rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fuggers_py._core.types import Date


class StubType(str, Enum):
    """Direction and length of a non-regular coupon period."""

    FRONT_SHORT = "FRONT_SHORT"
    FRONT_LONG = "FRONT_LONG"
    BACK_SHORT = "BACK_SHORT"
    BACK_LONG = "BACK_LONG"

    def is_front_stub(self) -> bool:
        return self in {StubType.FRONT_SHORT, StubType.FRONT_LONG}


@dataclass(frozen=True, slots=True)
class StubPeriodRules:
    """Schedule stub configuration used by coupon schedules."""

    stub_type: StubType | None = None
    first_regular_date: Date | None = None
    penultimate_date: Date | None = None

    @classmethod
    def none(cls) -> "StubPeriodRules":
        return cls(stub_type=None, first_regular_date=None, penultimate_date=None)

    @classmethod
    def default(cls) -> "StubPeriodRules":
        return cls.none()


__all__ = ["StubPeriodRules", "StubType"]
