"""Portfolio risk aggregation (`fuggers_py.measures.risk.hedging.portfolio`).

Portfolio aggregation uses absolute market values for weighting and sums DV01
as a positive-magnitude exposure measure.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..dv01 import dv01_from_duration


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class Position:
    """Single portfolio position for risk aggregation.

    Parameters
    ----------
    modified_duration:
        Position modified duration in years.
    dirty_price:
        Dirty price in percent of par.
    face:
        Face notional in currency units.
    """

    modified_duration: Decimal
    dirty_price: Decimal
    face: Decimal = Decimal(100)

    def dv01(self) -> Decimal:
        """Return the position DV01."""

        return dv01_from_duration(self.modified_duration, self.dirty_price, self.face)

    def market_value(self) -> Decimal:
        """Return the position market value in currency units."""

        return self.dirty_price * self.face / Decimal(100)


@dataclass(frozen=True, slots=True)
class PortfolioRisk:
    """Aggregated portfolio risk summary.

    Attributes
    ----------
    dv01:
        Sum of position DV01 values in currency units.
    weighted_duration:
        Absolute-market-value-weighted modified duration.
    """

    dv01: Decimal
    weighted_duration: Decimal


def aggregate_portfolio_risk(positions: list[Position]) -> PortfolioRisk:
    """Aggregate DV01 and market-value-weighted duration across positions.

    Returns
    -------
    PortfolioRisk
        Aggregate risk summary for the supplied positions. An empty input
        returns zeros.
    """

    if not positions:
        return PortfolioRisk(dv01=Decimal(0), weighted_duration=Decimal(0))

    total_dv01 = Decimal(0)
    weighted_duration_numerator = Decimal(0)
    gross_market_value = Decimal(0)

    for pos in positions:
        dv01 = pos.dv01()
        market_value = abs(pos.market_value())
        total_dv01 += dv01
        weighted_duration_numerator += pos.modified_duration * market_value
        gross_market_value += market_value

    avg_duration = weighted_duration_numerator / gross_market_value if gross_market_value != 0 else Decimal(0)
    return PortfolioRisk(dv01=total_dv01, weighted_duration=avg_duration)


__all__ = ["Position", "PortfolioRisk", "aggregate_portfolio_risk"]
