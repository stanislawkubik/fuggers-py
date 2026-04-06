"""Curve value-type definitions.

Value types describe the economic meaning of raw curve nodes.  The curve layer
keeps values as decimals rather than percentages, so the value type is what
distinguishes discount factors, zero rates, survival probabilities, hazard
rates, and spread-like conventions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Frequency, SpreadType

from .errors import InvalidCurveInput


class ValueTypeKind(StrEnum):
    """Semantic meaning of a curve node value."""

    DISCOUNT_FACTOR = "DISCOUNT_FACTOR"
    ZERO_RATE = "ZERO_RATE"
    FORWARD_RATE = "FORWARD_RATE"
    INSTANTANEOUS_FORWARD = "INSTANTANEOUS_FORWARD"
    SURVIVAL_PROBABILITY = "SURVIVAL_PROBABILITY"
    HAZARD_RATE = "HAZARD_RATE"
    CREDIT_SPREAD = "CREDIT_SPREAD"
    INFLATION_INDEX_RATIO = "INFLATION_INDEX_RATIO"
    FX_FORWARD_POINTS = "FX_FORWARD_POINTS"
    PAR_SWAP_RATE = "PAR_SWAP_RATE"

    def __str__(self) -> str:  # pragma: no cover - legacy public behavior
        return f"{self.__class__.__name__}.{self.name}"


@dataclass(frozen=True, slots=True)
class ValueType:
    """Describe how values on a term structure should be interpreted.

    The optional fields depend on ``kind``. Zero-rate types carry compounding
    and day-count information, forward-rate types carry tenor plus compounding,
    and credit-spread types carry spread-type plus recovery assumptions.

    All numeric attributes are stored as raw decimals.  Recovery is a fraction
    in ``[0, 1]`` and tenors are expressed in years.
    """

    kind: ValueTypeKind
    compounding: Compounding | None = None
    day_count: DayCountConvention | None = None
    tenor: float | None = None
    spread_type: SpreadType | None = None
    recovery: float | None = None
    frequency: Frequency | None = None

    def __post_init__(self) -> None:
        match self.kind:
            case (
                ValueTypeKind.DISCOUNT_FACTOR
                | ValueTypeKind.INSTANTANEOUS_FORWARD
                | ValueTypeKind.SURVIVAL_PROBABILITY
                | ValueTypeKind.HAZARD_RATE
                | ValueTypeKind.INFLATION_INDEX_RATIO
                | ValueTypeKind.FX_FORWARD_POINTS
            ):
                if any(
                    field is not None
                    for field in (
                        self.compounding,
                        self.day_count,
                        self.tenor,
                        self.spread_type,
                        self.recovery,
                        self.frequency,
                    )
                ):
                    raise InvalidCurveInput(f"ValueType.{self.kind.value} carries no fields.")
            case ValueTypeKind.ZERO_RATE:
                if self.compounding is None or self.day_count is None:
                    raise InvalidCurveInput("ValueType.ZERO_RATE requires compounding and day_count.")
                if any(
                    field is not None
                    for field in (
                        self.tenor,
                        self.spread_type,
                        self.recovery,
                        self.frequency,
                    )
                ):
                    raise InvalidCurveInput("ValueType.ZERO_RATE only supports compounding and day_count fields.")
            case ValueTypeKind.FORWARD_RATE:
                if self.tenor is None or self.compounding is None:
                    raise InvalidCurveInput("ValueType.FORWARD_RATE requires tenor and compounding.")
                if any(
                    field is not None
                    for field in (
                        self.day_count,
                        self.spread_type,
                        self.recovery,
                        self.frequency,
                    )
                ):
                    raise InvalidCurveInput("ValueType.FORWARD_RATE only supports tenor and compounding fields.")
            case ValueTypeKind.CREDIT_SPREAD:
                if self.spread_type is None or self.recovery is None:
                    raise InvalidCurveInput("ValueType.CREDIT_SPREAD requires spread_type and recovery.")
                if any(
                    field is not None
                    for field in (
                        self.compounding,
                        self.day_count,
                        self.tenor,
                        self.frequency,
                    )
                ):
                    raise InvalidCurveInput("ValueType.CREDIT_SPREAD only supports spread_type and recovery fields.")
            case ValueTypeKind.PAR_SWAP_RATE:
                if self.frequency is None or self.day_count is None:
                    raise InvalidCurveInput("ValueType.PAR_SWAP_RATE requires frequency and day_count.")
                if any(
                    field is not None
                    for field in (
                        self.compounding,
                        self.tenor,
                        self.spread_type,
                        self.recovery,
                    )
                ):
                    raise InvalidCurveInput("ValueType.PAR_SWAP_RATE only supports frequency and day_count fields.")
            case _:
                raise InvalidCurveInput(f"Unsupported ValueType kind: {self.kind!r}.")

    @classmethod
    def discount_factor(cls) -> ValueType:
        """Return a discount-factor value type."""

        return cls(ValueTypeKind.DISCOUNT_FACTOR)

    @classmethod
    def survival_probability(cls) -> ValueType:
        """Return a survival-probability value type."""

        return cls(ValueTypeKind.SURVIVAL_PROBABILITY)

    @classmethod
    def inflation_index_ratio(cls) -> ValueType:
        """Return an inflation-index-ratio value type."""

        return cls(ValueTypeKind.INFLATION_INDEX_RATIO)

    @classmethod
    def fx_forward_points(cls) -> ValueType:
        """Return an FX-forward-points value type."""

        return cls(ValueTypeKind.FX_FORWARD_POINTS)

    @classmethod
    def instantaneous_forward(cls) -> ValueType:
        """Return an instantaneous-forward value type."""

        return cls(ValueTypeKind.INSTANTANEOUS_FORWARD)

    @classmethod
    def hazard_rate(cls) -> ValueType:
        """Return a hazard-rate value type."""

        return cls(ValueTypeKind.HAZARD_RATE)

    @classmethod
    def zero_rate(
        cls,
        compounding: Compounding,
        day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED,
    ) -> ValueType:
        """Return a zero-rate value type with explicit compounding metadata."""

        return cls(ValueTypeKind.ZERO_RATE, compounding=compounding, day_count=day_count)

    @classmethod
    def continuous_zero(cls, day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED) -> ValueType:
        """Return a continuously compounded zero-rate value type."""

        return cls.zero_rate(Compounding.CONTINUOUS, day_count)

    @classmethod
    def annual_zero(cls, day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED) -> ValueType:
        """Return an annually compounded zero-rate value type."""

        return cls.zero_rate(Compounding.ANNUAL, day_count)

    @classmethod
    def semi_annual_zero(cls, day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED) -> ValueType:
        """Return a semi-annually compounded zero-rate value type."""

        return cls.zero_rate(Compounding.SEMI_ANNUAL, day_count)

    @classmethod
    def forward_rate(cls, tenor: float, compounding: Compounding = Compounding.CONTINUOUS) -> ValueType:
        """Return a forward-rate value type for a forward tenor in years."""

        return cls(ValueTypeKind.FORWARD_RATE, tenor=float(tenor), compounding=compounding)

    @classmethod
    def forward_3m(cls, compounding: Compounding = Compounding.CONTINUOUS) -> ValueType:
        """Return a 3-month forward-rate value type."""

        return cls.forward_rate(0.25, compounding=compounding)

    @classmethod
    def forward_6m(cls, compounding: Compounding = Compounding.CONTINUOUS) -> ValueType:
        """Return a 6-month forward-rate value type."""

        return cls.forward_rate(0.5, compounding=compounding)

    @classmethod
    def credit_spread(cls, spread_type: SpreadType, recovery: float = 0.40) -> ValueType:
        """Return a credit-spread value type with recovery assumption."""

        return cls(ValueTypeKind.CREDIT_SPREAD, spread_type=spread_type, recovery=float(recovery))

    @classmethod
    def par_swap_rate(cls, frequency: Frequency, day_count: DayCountConvention) -> ValueType:
        """Return a par-swap-rate value type."""

        return cls(ValueTypeKind.PAR_SWAP_RATE, frequency=frequency, day_count=day_count)

    def can_convert_to_discount_factor(self) -> bool:
        """Return whether this value type can be mapped to discount factors."""

        return self.kind in {
            ValueTypeKind.DISCOUNT_FACTOR,
            ValueTypeKind.ZERO_RATE,
            ValueTypeKind.SURVIVAL_PROBABILITY,
        }

    def is_rate_type(self) -> bool:
        """Return whether this value type represents a rate-like quantity."""

        return self.kind in {
            ValueTypeKind.ZERO_RATE,
            ValueTypeKind.FORWARD_RATE,
            ValueTypeKind.INSTANTANEOUS_FORWARD,
            ValueTypeKind.HAZARD_RATE,
            ValueTypeKind.PAR_SWAP_RATE,
        }

    def is_probability_type(self) -> bool:
        """Return whether this value type is unitless and probability-like.

        Discount-factor and survival-probability curves are treated as
        probability-like because they can be converted to discount factors
        without extra market conventions.
        """

        return self.kind in {ValueTypeKind.DISCOUNT_FACTOR, ValueTypeKind.SURVIVAL_PROBABILITY}

    def is_credit_type(self) -> bool:
        """Return whether this value type is used in credit-curve workflows."""

        return self.kind in {ValueTypeKind.SURVIVAL_PROBABILITY, ValueTypeKind.HAZARD_RATE, ValueTypeKind.CREDIT_SPREAD}

    def short_name(self) -> str:
        """Return a compact display name for the value type."""

        match self.kind:
            case ValueTypeKind.DISCOUNT_FACTOR:
                return "DF"
            case ValueTypeKind.ZERO_RATE:
                return "Zero"
            case ValueTypeKind.FORWARD_RATE:
                return "Fwd"
            case ValueTypeKind.INSTANTANEOUS_FORWARD:
                return "InstFwd"
            case ValueTypeKind.SURVIVAL_PROBABILITY:
                return "Surv"
            case ValueTypeKind.HAZARD_RATE:
                return "Hazard"
            case ValueTypeKind.CREDIT_SPREAD:
                return "CrSprd"
            case ValueTypeKind.INFLATION_INDEX_RATIO:
                return "Infl"
            case ValueTypeKind.FX_FORWARD_POINTS:
                return "FxPts"
            case ValueTypeKind.PAR_SWAP_RATE:
                return "ParSwap"
        return str(self.kind)

    def __str__(self) -> str:  # pragma: no cover - trivial
        match self.kind:
            case ValueTypeKind.DISCOUNT_FACTOR:
                return "DiscountFactor"
            case ValueTypeKind.INSTANTANEOUS_FORWARD:
                return "InstantaneousForward"
            case ValueTypeKind.SURVIVAL_PROBABILITY:
                return "SurvivalProbability"
            case ValueTypeKind.HAZARD_RATE:
                return "HazardRate"
            case ValueTypeKind.INFLATION_INDEX_RATIO:
                return "InflationIndexRatio"
            case ValueTypeKind.FX_FORWARD_POINTS:
                return "FxForwardPoints"
            case ValueTypeKind.ZERO_RATE:
                assert self.compounding is not None and self.day_count is not None
                return f"ZeroRate({self.compounding}, {self.day_count.name()})"
            case ValueTypeKind.FORWARD_RATE:
                assert self.tenor is not None and self.compounding is not None
                return f"ForwardRate({self.tenor}, {self.compounding})"
            case ValueTypeKind.CREDIT_SPREAD:
                assert self.spread_type is not None and self.recovery is not None
                return f"CreditSpread({self.spread_type}, {self.recovery})"
            case ValueTypeKind.PAR_SWAP_RATE:
                assert self.frequency is not None and self.day_count is not None
                return f"ParSwapRate({self.frequency}, {self.day_count.name()})"
        return repr(self)
