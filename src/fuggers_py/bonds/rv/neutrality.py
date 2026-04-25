"""Deterministic neutrality helpers for fitted-bond RV trades.

Long legs are the cheap bond purchases and short legs are the rich bond sales.
Expected convergence is positive when the long leg rises toward fair value and
the short leg falls toward fair value.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Mapping

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.types import Compounding, Date, Yield
from fuggers_py.bonds import RiskMetrics
from fuggers_py._core.compounding import CompoundingKind

from ._fit_result import FittedBondResult
from .selection import BondChoice, MaturityChoice, SignalDirection


class NeutralityTarget(str, Enum):
    """Neutrality target used to size a paired RV trade."""

    DV01 = "DV01"
    NOTIONAL = "NOTIONAL"

    @classmethod
    def parse(cls, value: "NeutralityTarget | str") -> "NeutralityTarget":
        """Parse a neutrality target from a string or enum value."""
        if isinstance(value, cls):
            return value
        return cls[str(value).strip().upper()]


@dataclass(frozen=True, slots=True)
class TradeLeg:
    """Single trade leg with DV01 and residual metadata."""

    instrument_id: InstrumentId
    direction: SignalDirection
    notional: Decimal
    maturity_years: Decimal
    fitted_yield: Decimal
    dv01_per_100: Decimal
    price_residual: Decimal
    bp_residual: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "direction", SignalDirection.parse(self.direction))
        object.__setattr__(self, "notional", self.notional if isinstance(self.notional, Decimal) else Decimal(str(self.notional)))
        object.__setattr__(
            self,
            "maturity_years",
            self.maturity_years if isinstance(self.maturity_years, Decimal) else Decimal(str(self.maturity_years)),
        )
        object.__setattr__(
            self,
            "fitted_yield",
            self.fitted_yield if isinstance(self.fitted_yield, Decimal) else Decimal(str(self.fitted_yield)),
        )
        object.__setattr__(
            self,
            "dv01_per_100",
            self.dv01_per_100 if isinstance(self.dv01_per_100, Decimal) else Decimal(str(self.dv01_per_100)),
        )
        object.__setattr__(
            self,
            "price_residual",
            self.price_residual if isinstance(self.price_residual, Decimal) else Decimal(str(self.price_residual)),
        )
        object.__setattr__(
            self,
            "bp_residual",
            self.bp_residual if isinstance(self.bp_residual, Decimal) else Decimal(str(self.bp_residual)),
        )


@dataclass(frozen=True, slots=True)
class NeutralizedTradeExpression:
    """Two-leg RV trade sized to a neutrality target."""

    neutrality_target: NeutralityTarget
    hedge_ratio: Decimal
    gross_notional: Decimal
    net_dv01: Decimal
    expected_price_convergence: Decimal
    expected_bp_convergence: Decimal
    long_leg: TradeLeg
    short_leg: TradeLeg

    def __post_init__(self) -> None:
        object.__setattr__(self, "neutrality_target", NeutralityTarget.parse(self.neutrality_target))
        object.__setattr__(
            self,
            "hedge_ratio",
            self.hedge_ratio if isinstance(self.hedge_ratio, Decimal) else Decimal(str(self.hedge_ratio)),
        )
        object.__setattr__(
            self,
            "gross_notional",
            self.gross_notional if isinstance(self.gross_notional, Decimal) else Decimal(str(self.gross_notional)),
        )
        object.__setattr__(
            self,
            "net_dv01",
            self.net_dv01 if isinstance(self.net_dv01, Decimal) else Decimal(str(self.net_dv01)),
        )
        object.__setattr__(
            self,
            "expected_price_convergence",
            self.expected_price_convergence
            if isinstance(self.expected_price_convergence, Decimal)
            else Decimal(str(self.expected_price_convergence)),
        )
        object.__setattr__(
            self,
            "expected_bp_convergence",
            self.expected_bp_convergence
            if isinstance(self.expected_bp_convergence, Decimal)
            else Decimal(str(self.expected_bp_convergence)),
        )


def _point_from_choice(
    fit_result: FittedBondResult,
    choice: MaturityChoice | BondChoice,
) -> Mapping[str, object]:
    return fit_result.get_bond(choice.instrument_id)


def _trade_leg(
    point: Mapping[str, object],
    *,
    direction: SignalDirection,
    notional: Decimal,
    settlement_date: Date,
) -> TradeLeg:
    fitted_yield = point["fitted_yield"] if isinstance(point["fitted_yield"], Decimal) else Decimal(str(point["fitted_yield"]))
    method = point["bond"].rules().compounding
    if method.kind is CompoundingKind.CONTINUOUS:
        compounding = Compounding.CONTINUOUS
    elif method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        compounding = Compounding.SIMPLE
    elif method.frequency == 1:
        compounding = Compounding.ANNUAL
    elif method.frequency == 2:
        compounding = Compounding.SEMI_ANNUAL
    elif method.frequency == 4:
        compounding = Compounding.QUARTERLY
    else:
        compounding = Compounding.ANNUAL
    return TradeLeg(
        instrument_id=point["instrument_id"],
        direction=direction,
        notional=notional,
        maturity_years=point["maturity_years"],
        fitted_yield=fitted_yield,
        dv01_per_100=RiskMetrics.from_bond(
            point["bond"],
            Yield.new(fitted_yield, compounding),
            settlement_date,
        ).dv01,
        price_residual=point["price_residual"],
        bp_residual=point["bp_residual"],
    )


def neutralize_choices(
    fit_result: FittedBondResult,
    *,
    long_choice: MaturityChoice | BondChoice,
    short_choice: MaturityChoice | BondChoice,
    base_long_notional: object = Decimal("1000000"),
    neutrality_target: NeutralityTarget | str = NeutralityTarget.DV01,
) -> NeutralizedTradeExpression:
    """Build a neutralized long/short trade from fitted-bond choices.

    Under ``DV01`` neutrality the hedge ratio is ``long_dv01 / short_dv01``.
    Under ``NOTIONAL`` neutrality the long and short notionals match.
    """
    if long_choice.direction is not SignalDirection.LONG:
        raise ValueError("neutralize_choices requires long_choice.direction == LONG.")
    if short_choice.direction is not SignalDirection.SHORT:
        raise ValueError("neutralize_choices requires short_choice.direction == SHORT.")

    target = NeutralityTarget.parse(neutrality_target)
    base_notional = base_long_notional if isinstance(base_long_notional, Decimal) else Decimal(str(base_long_notional))
    if base_notional <= Decimal(0):
        raise ValueError("neutralize_choices requires a positive base_long_notional.")

    long_point = _point_from_choice(fit_result, long_choice)
    short_point = _point_from_choice(fit_result, short_choice)
    long_yield = (
        long_point["fitted_yield"]
        if isinstance(long_point["fitted_yield"], Decimal)
        else Decimal(str(long_point["fitted_yield"]))
    )
    long_method = long_point["bond"].rules().compounding
    if long_method.kind is CompoundingKind.CONTINUOUS:
        long_compounding = Compounding.CONTINUOUS
    elif long_method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        long_compounding = Compounding.SIMPLE
    elif long_method.frequency == 1:
        long_compounding = Compounding.ANNUAL
    elif long_method.frequency == 2:
        long_compounding = Compounding.SEMI_ANNUAL
    elif long_method.frequency == 4:
        long_compounding = Compounding.QUARTERLY
    else:
        long_compounding = Compounding.ANNUAL
    long_dv01 = RiskMetrics.from_bond(
        long_point["bond"],
        Yield.new(long_yield, long_compounding),
        fit_result.date(),
    ).dv01
    short_yield = (
        short_point["fitted_yield"]
        if isinstance(short_point["fitted_yield"], Decimal)
        else Decimal(str(short_point["fitted_yield"]))
    )
    short_method = short_point["bond"].rules().compounding
    if short_method.kind is CompoundingKind.CONTINUOUS:
        short_compounding = Compounding.CONTINUOUS
    elif short_method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        short_compounding = Compounding.SIMPLE
    elif short_method.frequency == 1:
        short_compounding = Compounding.ANNUAL
    elif short_method.frequency == 2:
        short_compounding = Compounding.SEMI_ANNUAL
    elif short_method.frequency == 4:
        short_compounding = Compounding.QUARTERLY
    else:
        short_compounding = Compounding.ANNUAL
    short_dv01 = RiskMetrics.from_bond(
        short_point["bond"],
        Yield.new(short_yield, short_compounding),
        fit_result.date(),
    ).dv01

    if target is NeutralityTarget.DV01:
        if short_dv01 == Decimal(0):
            raise ValueError("neutralize_choices requires a non-zero short-leg DV01 for DV01 neutrality.")
        hedge_ratio = long_dv01 / short_dv01
        short_notional = base_notional * hedge_ratio
    else:
        hedge_ratio = Decimal(1)
        short_notional = base_notional

    long_leg = _trade_leg(
        long_point,
        direction=SignalDirection.LONG,
        notional=base_notional,
        settlement_date=fit_result.date(),
    )
    short_leg = _trade_leg(
        short_point,
        direction=SignalDirection.SHORT,
        notional=short_notional,
        settlement_date=fit_result.date(),
    )
    net_dv01 = (base_notional / Decimal(100)) * long_dv01 - (short_notional / Decimal(100)) * short_dv01
    long_price_residual = (
        long_point["price_residual"]
        if isinstance(long_point["price_residual"], Decimal)
        else Decimal(str(long_point["price_residual"]))
    )
    short_price_residual = (
        short_point["price_residual"]
        if isinstance(short_point["price_residual"], Decimal)
        else Decimal(str(short_point["price_residual"]))
    )
    long_bp_residual = (
        long_point["bp_residual"]
        if isinstance(long_point["bp_residual"], Decimal)
        else Decimal(str(long_point["bp_residual"]))
    )
    short_bp_residual = (
        short_point["bp_residual"]
        if isinstance(short_point["bp_residual"], Decimal)
        else Decimal(str(short_point["bp_residual"]))
    )
    expected_price_convergence = (base_notional / Decimal(100)) * (-long_price_residual) + (
        short_notional / Decimal(100)
    ) * short_price_residual
    expected_bp_convergence = long_bp_residual - short_bp_residual
    return NeutralizedTradeExpression(
        neutrality_target=target,
        hedge_ratio=hedge_ratio,
        gross_notional=base_notional + short_notional,
        net_dv01=net_dv01,
        expected_price_convergence=expected_price_convergence,
        expected_bp_convergence=expected_bp_convergence,
        long_leg=long_leg,
        short_leg=short_leg,
    )


__all__ = [
    "NeutralityTarget",
    "NeutralizedTradeExpression",
    "TradeLeg",
    "neutralize_choices",
]
