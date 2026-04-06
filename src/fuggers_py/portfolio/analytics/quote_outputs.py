"""Portfolio aggregation on top of instrument quote outputs.

The portfolio analyzer works on top of bond quote outputs and optional
reference-data metadata to produce market-value, risk, and sector/rating
breakdowns.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.ids import InstrumentId, PortfolioId
from fuggers_py.market.snapshot import EtfHolding
from fuggers_py.calc.output import BondQuoteOutput, PortfolioAnalyticsOutput
from fuggers_py.reference.reference_data import BondReferenceData


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    """Quantity held in a single instrument."""

    instrument_id: InstrumentId
    quantity: Decimal


def _as_position(item: PortfolioPosition | EtfHolding) -> PortfolioPosition:
    if isinstance(item, PortfolioPosition):
        return item
    if item.quantity is None:
        raise ValueError("Portfolio positions require explicit quantities.")
    return PortfolioPosition(instrument_id=item.instrument_id, quantity=item.quantity)


@dataclass(frozen=True, slots=True)
class PortfolioAnalyzer:
    """Aggregate bond quote outputs into portfolio analytics."""

    def analyze(
        self,
        portfolio_id: PortfolioId | str | None,
        positions: list[PortfolioPosition | EtfHolding] | tuple[PortfolioPosition | EtfHolding, ...],
        quote_outputs: dict[InstrumentId, BondQuoteOutput],
        *,
        reference_data: dict[InstrumentId, BondReferenceData] | None = None,
    ) -> PortfolioAnalyticsOutput:
        """Aggregate positions into portfolio-level market value and risk.

        Holdings without a quote are skipped. Risk metrics are value weighted
        by dirty value, and the output includes sector and rating breakdowns
        when reference data is supplied.
        """
        total_market_value = Decimal(0)
        total_dirty_value = Decimal(0)
        aggregate_dv01 = Decimal(0)
        weighted_duration = Decimal(0)
        weighted_convexity = Decimal(0)
        weighted_z_spread = Decimal(0)
        weighted_g_spread = Decimal(0)
        weighted_i_spread = Decimal(0)
        key_rate_durations: dict[str, Decimal] = {}
        sector_breakdown: dict[str, Decimal] = {}
        rating_breakdown: dict[str, Decimal] = {}
        priced_count = 0

        for item in positions:
            position = _as_position(item)
            quote = quote_outputs.get(position.instrument_id)
            if quote is None or quote.clean_price is None:
                continue
            market_value = quote.clean_price * position.quantity
            dirty_value = (quote.dirty_price or quote.clean_price) * position.quantity
            priced_count += 1
            total_market_value += market_value
            total_dirty_value += dirty_value
            aggregate_dv01 += (quote.dv01 or Decimal(0)) * position.quantity / Decimal(100)
            weighted_duration += dirty_value * (quote.modified_duration or quote.effective_duration or Decimal(0))
            weighted_convexity += dirty_value * (quote.convexity or quote.effective_convexity or Decimal(0))
            weighted_z_spread += dirty_value * (quote.z_spread or Decimal(0))
            weighted_g_spread += dirty_value * (quote.g_spread or Decimal(0))
            weighted_i_spread += dirty_value * (quote.i_spread or Decimal(0))
            for tenor, value in quote.key_rate_durations.items():
                key_rate_durations[tenor] = key_rate_durations.get(tenor, Decimal(0)) + (value * position.quantity)

            metadata = None if reference_data is None else reference_data.get(position.instrument_id)
            if metadata is not None:
                if metadata.sector is not None:
                    sector_breakdown[metadata.sector] = sector_breakdown.get(metadata.sector, Decimal(0)) + market_value
                if metadata.rating is not None:
                    rating_breakdown[metadata.rating] = rating_breakdown.get(metadata.rating, Decimal(0)) + market_value

        denominator = total_dirty_value if total_dirty_value != 0 else Decimal(1)
        resolved_id = None if portfolio_id is None else (
            portfolio_id if isinstance(portfolio_id, PortfolioId) else PortfolioId.parse(portfolio_id)
        )
        return PortfolioAnalyticsOutput(
            portfolio_id=resolved_id,
            total_market_value=total_market_value,
            total_dirty_value=total_dirty_value,
            weighted_duration=weighted_duration / denominator if total_dirty_value else Decimal(0),
            weighted_convexity=weighted_convexity / denominator if total_dirty_value else Decimal(0),
            aggregate_dv01=aggregate_dv01,
            weighted_z_spread=weighted_z_spread / denominator if total_dirty_value else Decimal(0),
            weighted_g_spread=weighted_g_spread / denominator if total_dirty_value else Decimal(0),
            weighted_i_spread=weighted_i_spread / denominator if total_dirty_value else Decimal(0),
            key_rate_durations=key_rate_durations,
            sector_breakdown=sector_breakdown,
            rating_breakdown=rating_breakdown,
            position_count=len(positions),
            priced_count=priced_count,
            fully_priced=priced_count == len(positions),
        )


__all__ = ["PortfolioAnalyzer", "PortfolioPosition"]
