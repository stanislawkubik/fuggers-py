"""Index conventions for FRNs and overnight instruments.

The records in this module describe how a reference index resets, compounds,
observes, and publishes fixings, especially for overnight coupons.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from fuggers_py.core.daycounts import DayCountConvention

if TYPE_CHECKING:
    from .overnight import OvernightCompounding, PublicationTime


class ArrearConvention(str, Enum):
    """Coupon reset timing relative to the accrual period."""

    IN_ADVANCE = "IN_ADVANCE"
    IN_ARREARS = "IN_ARREARS"


class ObservationShiftType(str, Enum):
    """Observation-date adjustment applied to overnight fixings."""

    NONE = "NONE"
    LOOKBACK = "LOOKBACK"
    OBSERVATION_SHIFT = "OBSERVATION_SHIFT"


ShiftType = ObservationShiftType


@dataclass(frozen=True, slots=True)
class LookbackDays:
    """Business-day lookback applied to overnight observations."""

    days: int = 0

    def __int__(self) -> int:
        return self.days


@dataclass(frozen=True, slots=True)
class LockoutDays:
    """Final business days that reuse an earlier overnight fixing."""

    days: int = 0

    def __int__(self) -> int:
        return self.days


@dataclass(frozen=True, slots=True)
class IndexConventions:
    """Conventions for floating-rate and overnight reference indices.

    The object captures the day-count basis, arrears timing, overnight
    compounding mode, publication lag, and observation-shift behavior used to
    price coupons from the index.
    """

    day_count: DayCountConvention = DayCountConvention.ACT_360
    arrear_convention: ArrearConvention = ArrearConvention.IN_ARREARS
    overnight_compounding: "OvernightCompounding" | None = None
    publication_time: "PublicationTime" | None = None
    publication_lag_days: int = 0
    shift_type: ObservationShiftType = ObservationShiftType.NONE
    lookback_days: int = 0
    lockout_days: int = 0
    rate_cutoff_days: int = 0

    def __post_init__(self) -> None:
        from .overnight import OvernightCompounding, PublicationTime

        if self.overnight_compounding is None:
            object.__setattr__(self, "overnight_compounding", OvernightCompounding.COMPOUNDED)
        if self.publication_time is None:
            object.__setattr__(self, "publication_time", PublicationTime.SAME_DAY)

    @property
    def observation_shift_type(self) -> ObservationShiftType:
        """Return the configured observation-shift mode."""

        return self.shift_type

    @property
    def observation_shift_days(self) -> int:
        """Return the effective observation shift in business days."""

        if self.shift_type is ObservationShiftType.OBSERVATION_SHIFT:
            return self.lookback_days
        return 0


__all__ = [
    "ArrearConvention",
    "IndexConventions",
    "LockoutDays",
    "LookbackDays",
    "ObservationShiftType",
    "ShiftType",
]
