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

from fuggers_py.pricers.bonds.risk import RiskMetrics
from fuggers_py.reference.bonds.types import CompoundingKind
from fuggers_py.core.types import Compounding, Yield
from fuggers_py.market.curves.fitted_bonds import FittedBondCurve
from fuggers_py.core.ids import InstrumentId
from fuggers_py.core.types import Date

from .selection import BondChoice, MaturityChoice, SignalDirection


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _yield_from_decimal(bond, yield_value: Decimal) -> Yield:
    method = bond.rules().compounding
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
    return Yield.new(yield_value, compounding)


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
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "maturity_years", _to_decimal(self.maturity_years))
        object.__setattr__(self, "fitted_yield", _to_decimal(self.fitted_yield))
        object.__setattr__(self, "dv01_per_100", _to_decimal(self.dv01_per_100))
        object.__setattr__(self, "price_residual", _to_decimal(self.price_residual))
        object.__setattr__(self, "bp_residual", _to_decimal(self.bp_residual))


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
        object.__setattr__(self, "hedge_ratio", _to_decimal(self.hedge_ratio))
        object.__setattr__(self, "gross_notional", _to_decimal(self.gross_notional))
        object.__setattr__(self, "net_dv01", _to_decimal(self.net_dv01))
        object.__setattr__(self, "expected_price_convergence", _to_decimal(self.expected_price_convergence))
        object.__setattr__(self, "expected_bp_convergence", _to_decimal(self.expected_bp_convergence))


def _point_risk(point: Mapping[str, object], *, settlement_date: Date) -> Decimal:
    return RiskMetrics.from_bond(
        point["bond"],
        _yield_from_decimal(point["bond"], _to_decimal(point["fitted_yield"])),
        settlement_date,
    ).dv01


def _point_from_choice(
    fit_result: FittedBondCurve,
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
    return TradeLeg(
        instrument_id=point["instrument_id"],
        direction=direction,
        notional=notional,
        maturity_years=_to_decimal(point["maturity_years"]),
        fitted_yield=_to_decimal(point["fitted_yield"]),
        dv01_per_100=_point_risk(point, settlement_date=settlement_date),
        price_residual=_to_decimal(point["price_residual"]),
        bp_residual=_to_decimal(point["bp_residual"]),
    )


def neutralize_choices(
    fit_result: FittedBondCurve,
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
    base_notional = _to_decimal(base_long_notional)
    if base_notional <= Decimal(0):
        raise ValueError("neutralize_choices requires a positive base_long_notional.")

    long_point = _point_from_choice(fit_result, long_choice)
    short_point = _point_from_choice(fit_result, short_choice)
    long_dv01 = _point_risk(long_point, settlement_date=fit_result.reference_date)
    short_dv01 = _point_risk(short_point, settlement_date=fit_result.reference_date)

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
        settlement_date=fit_result.reference_date,
    )
    short_leg = _trade_leg(
        short_point,
        direction=SignalDirection.SHORT,
        notional=short_notional,
        settlement_date=fit_result.reference_date,
    )
    net_dv01 = (base_notional / Decimal(100)) * long_dv01 - (short_notional / Decimal(100)) * short_dv01
    expected_price_convergence = (base_notional / Decimal(100)) * (-_to_decimal(long_point["price_residual"])) + (
        short_notional / Decimal(100)
    ) * _to_decimal(short_point["price_residual"])
    expected_bp_convergence = _to_decimal(long_point["bp_residual"]) - _to_decimal(short_point["bp_residual"])
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


def neutralize_bond_pair(
    fit_result: FittedBondCurve,
    *,
    long_instrument_id: InstrumentId | str,
    short_instrument_id: InstrumentId | str,
    base_long_notional: object = Decimal("1000000"),
    neutrality_target: NeutralityTarget | str = NeutralityTarget.DV01,
) -> NeutralizedTradeExpression:
    """Build a neutralized long/short trade from instrument identifiers."""
    long_point = fit_result.get_bond(long_instrument_id)
    short_point = fit_result.get_bond(short_instrument_id)
    return neutralize_choices(
        fit_result,
        long_choice=BondChoice(
            signal_name="long_leg",
            direction=SignalDirection.LONG,
            score=Decimal(1),
            instrument_id=long_point["instrument_id"],
            maturity_years=_to_decimal(long_point["maturity_years"]),
            bp_residual=_to_decimal(long_point["bp_residual"]),
            price_residual=_to_decimal(long_point["price_residual"]),
        ),
        short_choice=BondChoice(
            signal_name="short_leg",
            direction=SignalDirection.SHORT,
            score=Decimal(-1),
            instrument_id=short_point["instrument_id"],
            maturity_years=_to_decimal(short_point["maturity_years"]),
            bp_residual=_to_decimal(short_point["bp_residual"]),
            price_residual=_to_decimal(short_point["price_residual"]),
        ),
        base_long_notional=base_long_notional,
        neutrality_target=neutrality_target,
    )


__all__ = [
    "NeutralityTarget",
    "NeutralizedTradeExpression",
    "TradeLeg",
    "neutralize_bond_pair",
    "neutralize_choices",
]
