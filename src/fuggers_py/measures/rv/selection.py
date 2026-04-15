"""Deterministic hooks from external signals into fitted-bond choices.

Selection preserves the fitted-bond residual conventions: basis-point residuals
greater than zero mean cheap, while negative residuals mean rich.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Mapping

from fuggers_py.core.ids import InstrumentId
from fuggers_py.market.curves.fitted_bonds import BondCurve


class SignalDirection(str, Enum):
    """Signal polarity used to map external views into long/short choices."""

    LONG = "LONG"
    SHORT = "SHORT"

    @classmethod
    def parse(cls, value: "SignalDirection | str") -> "SignalDirection":
        """Parse a signal direction from a string or enum value."""
        if isinstance(value, cls):
            return value
        return cls[str(value).strip().upper()]


def _resolved_direction(direction: SignalDirection | str | None, *, score: Decimal) -> SignalDirection:
    if direction is not None:
        return SignalDirection.parse(direction)
    return SignalDirection.LONG if score >= Decimal(0) else SignalDirection.SHORT


@dataclass(frozen=True, slots=True)
class MaturitySignal:
    """Signal describing a desired maturity bucket and directional score."""

    name: str
    target_maturity_years: Decimal
    score: Decimal
    direction: SignalDirection | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(
            self,
            "target_maturity_years",
            self.target_maturity_years
            if isinstance(self.target_maturity_years, Decimal)
            else Decimal(str(self.target_maturity_years)),
        )
        object.__setattr__(self, "score", self.score if isinstance(self.score, Decimal) else Decimal(str(self.score)))
        if self.direction is not None:
            object.__setattr__(self, "direction", SignalDirection.parse(self.direction))
        if not self.name:
            raise ValueError("MaturitySignal name must be non-empty.")
        if self.target_maturity_years <= Decimal(0):
            raise ValueError("MaturitySignal target_maturity_years must be positive.")

    def resolved_direction(self) -> SignalDirection:
        """Resolve the signal direction, defaulting from the score sign."""
        return _resolved_direction(self.direction, score=self.score)


@dataclass(frozen=True, slots=True)
class BondSignal:
    """Signal describing a specific bond and directional score."""

    name: str
    instrument_id: InstrumentId
    score: Decimal
    direction: SignalDirection | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "score", self.score if isinstance(self.score, Decimal) else Decimal(str(self.score)))
        if self.direction is not None:
            object.__setattr__(self, "direction", SignalDirection.parse(self.direction))
        if not self.name:
            raise ValueError("BondSignal name must be non-empty.")

    def resolved_direction(self) -> SignalDirection:
        """Resolve the signal direction, defaulting from the score sign."""
        return _resolved_direction(self.direction, score=self.score)


@dataclass(frozen=True, slots=True)
class MaturityChoice:
    """Selected fitted bond for a maturity-based signal."""

    signal_name: str
    direction: SignalDirection
    score: Decimal
    instrument_id: InstrumentId
    target_maturity_years: Decimal
    maturity_years: Decimal
    maturity_gap_years: Decimal
    bp_residual: Decimal
    price_residual: Decimal
    benchmark_flag: bool | None = None
    liquidity_score: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_name", self.signal_name.strip())
        object.__setattr__(self, "direction", SignalDirection.parse(self.direction))
        object.__setattr__(self, "score", self.score if isinstance(self.score, Decimal) else Decimal(str(self.score)))
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(
            self,
            "target_maturity_years",
            self.target_maturity_years
            if isinstance(self.target_maturity_years, Decimal)
            else Decimal(str(self.target_maturity_years)),
        )
        object.__setattr__(
            self,
            "maturity_years",
            self.maturity_years if isinstance(self.maturity_years, Decimal) else Decimal(str(self.maturity_years)),
        )
        object.__setattr__(
            self,
            "maturity_gap_years",
            self.maturity_gap_years
            if isinstance(self.maturity_gap_years, Decimal)
            else Decimal(str(self.maturity_gap_years)),
        )
        object.__setattr__(
            self,
            "bp_residual",
            self.bp_residual if isinstance(self.bp_residual, Decimal) else Decimal(str(self.bp_residual)),
        )
        object.__setattr__(
            self,
            "price_residual",
            self.price_residual if isinstance(self.price_residual, Decimal) else Decimal(str(self.price_residual)),
        )
        if self.liquidity_score is not None:
            object.__setattr__(
                self,
                "liquidity_score",
                self.liquidity_score if isinstance(self.liquidity_score, Decimal) else Decimal(str(self.liquidity_score)),
            )


@dataclass(frozen=True, slots=True)
class BondChoice:
    """Selected fitted bond for a bond-specific signal."""

    signal_name: str
    direction: SignalDirection
    score: Decimal
    instrument_id: InstrumentId
    maturity_years: Decimal
    bp_residual: Decimal
    price_residual: Decimal
    benchmark_flag: bool | None = None
    liquidity_score: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_name", self.signal_name.strip())
        object.__setattr__(self, "direction", SignalDirection.parse(self.direction))
        object.__setattr__(self, "score", self.score if isinstance(self.score, Decimal) else Decimal(str(self.score)))
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(
            self,
            "maturity_years",
            self.maturity_years if isinstance(self.maturity_years, Decimal) else Decimal(str(self.maturity_years)),
        )
        object.__setattr__(
            self,
            "bp_residual",
            self.bp_residual if isinstance(self.bp_residual, Decimal) else Decimal(str(self.bp_residual)),
        )
        object.__setattr__(
            self,
            "price_residual",
            self.price_residual if isinstance(self.price_residual, Decimal) else Decimal(str(self.price_residual)),
        )
        if self.liquidity_score is not None:
            object.__setattr__(
                self,
                "liquidity_score",
                self.liquidity_score if isinstance(self.liquidity_score, Decimal) else Decimal(str(self.liquidity_score)),
            )


def _eligible_points(
    fit_result: BondCurve,
    *,
    benchmark_only: bool = False,
    minimum_liquidity_score: object | None = None,
) -> tuple[Mapping[str, object], ...]:
    minimum_liquidity = (
        None
        if minimum_liquidity_score is None
        else minimum_liquidity_score
        if isinstance(minimum_liquidity_score, Decimal)
        else Decimal(str(minimum_liquidity_score))
    )
    candidates: list[Mapping[str, object]] = []
    for point in fit_result.bonds:
        reference_data = point.get("reference_data")
        benchmark_flag = None if reference_data is None else reference_data.benchmark_flag
        liquidity_score = (
            None
            if reference_data is None or reference_data.liquidity_score is None
            else reference_data.liquidity_score
            if isinstance(reference_data.liquidity_score, Decimal)
            else Decimal(str(reference_data.liquidity_score))
        )
        if benchmark_only and benchmark_flag is not True:
            continue
        if minimum_liquidity is not None:
            if liquidity_score is None or liquidity_score < minimum_liquidity:
                continue
        candidates.append(point)
    if not candidates:
        raise ValueError("No fitted-bond candidates satisfy the requested selection filters.")
    return tuple(candidates)


def select_maturity_choice(
    fit_result: BondCurve,
    signal: MaturitySignal,
    *,
    benchmark_only: bool = False,
    minimum_liquidity_score: object | None = None,
) -> MaturityChoice:
    """Select the fitted bond closest to a maturity signal."""
    candidates = _eligible_points(
        fit_result,
        benchmark_only=benchmark_only,
        minimum_liquidity_score=minimum_liquidity_score,
    )
    def _maturity_years(point: Mapping[str, object]) -> Decimal:
        value = point["maturity_years"]
        return value if isinstance(value, Decimal) else Decimal(str(value))

    chosen = min(
        candidates,
        key=lambda point: (
            abs(_maturity_years(point) - signal.target_maturity_years),
            0 if point.get("reference_data") and point["reference_data"].benchmark_flag else 1,
            -(
                point["reference_data"].liquidity_score
                if point.get("reference_data") and point["reference_data"].liquidity_score is not None
                else Decimal(0)
            ),
            point["instrument_id"].as_str(),
        ),
    )
    chosen_maturity = _maturity_years(chosen)
    reference_data = chosen.get("reference_data")
    benchmark_flag = None if reference_data is None else reference_data.benchmark_flag
    liquidity_score = (
        None
        if reference_data is None or reference_data.liquidity_score is None
        else reference_data.liquidity_score
        if isinstance(reference_data.liquidity_score, Decimal)
        else Decimal(str(reference_data.liquidity_score))
    )
    return MaturityChoice(
        signal_name=signal.name,
        direction=signal.resolved_direction(),
        score=signal.score,
        instrument_id=chosen["instrument_id"],
        target_maturity_years=signal.target_maturity_years,
        maturity_years=chosen_maturity,
        maturity_gap_years=abs(chosen_maturity - signal.target_maturity_years),
        bp_residual=chosen["bp_residual"],
        price_residual=chosen["price_residual"],
        benchmark_flag=benchmark_flag,
        liquidity_score=liquidity_score,
    )


def select_bond_choice(fit_result: BondCurve, signal: BondSignal) -> BondChoice:
    """Select the fitted bond referenced by a bond signal."""
    point = fit_result.get_bond(signal.instrument_id)
    reference_data = point.get("reference_data")
    benchmark_flag = None if reference_data is None else reference_data.benchmark_flag
    liquidity_score = (
        None
        if reference_data is None or reference_data.liquidity_score is None
        else reference_data.liquidity_score
        if isinstance(reference_data.liquidity_score, Decimal)
        else Decimal(str(reference_data.liquidity_score))
    )
    return BondChoice(
        signal_name=signal.name,
        direction=signal.resolved_direction(),
        score=signal.score,
        instrument_id=point["instrument_id"],
        maturity_years=point["maturity_years"],
        bp_residual=point["bp_residual"],
        price_residual=point["price_residual"],
        benchmark_flag=benchmark_flag,
        liquidity_score=liquidity_score,
    )


__all__ = [
    "BondChoice",
    "BondSignal",
    "MaturityChoice",
    "MaturitySignal",
    "SignalDirection",
    "select_bond_choice",
    "select_maturity_choice",
]
