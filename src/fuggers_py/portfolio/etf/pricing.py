"""ETF-style aggregation on top of instrument quote outputs.

The ETF pricer reuses bond quote outputs to aggregate NAV, market value, and
risk exposures across holdings.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.ids import EtfId, InstrumentId
from fuggers_py.market.snapshot import EtfHolding
from fuggers_py.calc.output import BondQuoteOutput, EtfAnalyticsOutput


def _holding_value(holding: EtfHolding, quote: BondQuoteOutput) -> Decimal | None:
    price = quote.dirty_price if quote.dirty_price is not None else quote.clean_price
    if price is None:
        return None
    if holding.quantity is None:
        return None
    return price * holding.quantity


@dataclass(frozen=True, slots=True)
class EtfPricer:
    """Aggregate bond quote outputs into ETF-style analytics."""

    def price(
        self,
        etf_id: EtfId | str | None,
        holdings: list[EtfHolding] | tuple[EtfHolding, ...],
        quote_outputs: dict[InstrumentId, BondQuoteOutput],
        *,
        shares_outstanding: Decimal,
    ) -> EtfAnalyticsOutput:
        """Aggregate holding-level outputs into an ETF analytics record.

        The pricer sums value-weighted risk outputs across holdings and returns
        an ETF-style analytics record with NAV, per-share metrics, and
        aggregation counts.
        """
        total_value = Decimal(0)
        weighted_duration = Decimal(0)
        weighted_convexity = Decimal(0)
        weighted_z_spread = Decimal(0)
        weighted_g_spread = Decimal(0)
        weighted_i_spread = Decimal(0)
        aggregate_dv01 = Decimal(0)
        priced_count = 0

        for holding in holdings:
            quote = quote_outputs.get(holding.instrument_id)
            if quote is None:
                continue
            holding_value = _holding_value(holding, quote)
            if holding_value is None:
                continue
            priced_count += 1
            total_value += holding_value
            if holding.quantity is not None:
                aggregate_dv01 += (quote.dv01 or Decimal(0)) * holding.quantity / Decimal(100)
            weighted_duration += holding_value * (quote.modified_duration or quote.effective_duration or Decimal(0))
            weighted_convexity += holding_value * (quote.convexity or quote.effective_convexity or Decimal(0))
            weighted_z_spread += holding_value * (quote.z_spread or Decimal(0))
            weighted_g_spread += holding_value * (quote.g_spread or Decimal(0))
            weighted_i_spread += holding_value * (quote.i_spread or Decimal(0))

        denominator = total_value if total_value != 0 else Decimal(1)
        resolved_id = None if etf_id is None else (etf_id if isinstance(etf_id, EtfId) else EtfId.parse(etf_id))
        nav = total_value / shares_outstanding
        return EtfAnalyticsOutput(
            etf_id=resolved_id,
            gross_market_value=total_value,
            nav=nav,
            inav=nav,
            shares_outstanding=shares_outstanding,
            weighted_duration=weighted_duration / denominator if total_value else Decimal(0),
            weighted_convexity=weighted_convexity / denominator if total_value else Decimal(0),
            aggregate_dv01=aggregate_dv01,
            weighted_z_spread=weighted_z_spread / denominator if total_value else Decimal(0),
            weighted_g_spread=weighted_g_spread / denominator if total_value else Decimal(0),
            weighted_i_spread=weighted_i_spread / denominator if total_value else Decimal(0),
            holding_count=len(holdings),
            priced_count=priced_count,
            fully_priced=priced_count == len(holdings),
        )


__all__ = ["EtfPricer"]
