"""Research-facing pricing specifications.

The pricing-spec layer separates quote-side selection from benchmark
selection, spread quoting, and optional risk toggles used by the pricing
engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py.reference.bonds.types import ASWType, Tenor

from fuggers_py.core.ids import CurveId
from fuggers_py.market.state import QuoteSide


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class BenchmarkReference:
    """Benchmark selector by curve identifier or tenor string.

    Exactly one of `curve_id` or `tenor` should be set. The object is used to
    route spread calculations and benchmark-dependent analytics without forcing
    the caller to resolve the benchmark upfront.
    """

    curve_id: CurveId | None = None
    tenor: str | None = None

    @classmethod
    def by_curve(cls, curve_id: CurveId | str) -> "BenchmarkReference":
        """Create a benchmark reference from a curve identifier."""
        return cls(curve_id=curve_id if isinstance(curve_id, CurveId) else CurveId.parse(curve_id))

    @classmethod
    def by_tenor(cls, tenor: str) -> "BenchmarkReference":
        """Create a benchmark reference from a validated tenor string."""
        Tenor.parse(tenor)
        return cls(tenor=tenor)

    def tenor_object(self) -> Tenor | None:
        """Return the parsed tenor object when a tenor was supplied."""
        return None if self.tenor is None else Tenor.parse(self.tenor)


@dataclass(frozen=True, slots=True)
class BidAskSpreadConfig:
    """Mid-to-side spread adjustments expressed in decimal units.

    The adjustments are added to a mid value to produce the bid or ask quote.
    Positive values move the quote away from mid on the ask side and toward the
    bid side on the bid side only if the caller supplies symmetric widths via
    :meth:`symmetric`.
    """

    bid_adjustment: Decimal = Decimal(0)
    ask_adjustment: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        object.__setattr__(self, "bid_adjustment", _to_decimal(self.bid_adjustment))
        object.__setattr__(self, "ask_adjustment", _to_decimal(self.ask_adjustment))

    @classmethod
    def symmetric(cls, width: object) -> "BidAskSpreadConfig":
        """Build symmetric bid/ask adjustments from a total width."""
        half_width = _to_decimal(width) / Decimal(2)
        return cls(bid_adjustment=-half_width, ask_adjustment=half_width)

    @classmethod
    def asymmetric(cls, *, bid_adjustment: object, ask_adjustment: object) -> "BidAskSpreadConfig":
        """Build bid and ask adjustments from explicit offsets."""
        return cls(bid_adjustment=_to_decimal(bid_adjustment), ask_adjustment=_to_decimal(ask_adjustment))

    def adjust(self, mid_value: object, side: QuoteSide) -> Decimal:
        """Return the side-specific quote implied by ``mid_value``."""
        mid = _to_decimal(mid_value)
        if side is QuoteSide.BID:
            return mid + self.bid_adjustment
        if side is QuoteSide.ASK:
            return mid + self.ask_adjustment
        return mid


@dataclass(frozen=True, slots=True)
class PricingSpec:
    """Pricing engine configuration and output selection toggles.

    This record controls how the router interprets the market price, which risk
    and spread fields to compute, whether callable and floating paths should use
    auxiliary spread measures, and which benchmark or bid/ask adjustments to
    apply. Rates, spreads, and vol inputs remain in raw decimal units.
    """

    quote_side: QuoteSide = QuoteSide.MID
    market_price_is_dirty: bool | None = None
    compute_spreads: bool = True
    compute_risk: bool = True
    compute_key_rates: bool = False
    compute_current_yield: bool = True
    compute_yield_to_worst: bool = True
    include_asset_swap: bool = False
    asset_swap_type: ASWType = ASWType.PAR_PAR
    route_callable_with_oas: bool = True
    route_floating_with_discount_margin: bool = True
    callable_mean_reversion: Decimal = Decimal("0.03")
    callable_volatility: Decimal = Decimal("0.01")
    benchmark_reference: BenchmarkReference | None = None
    bid_ask: BidAskSpreadConfig | None = None


__all__ = [
    "BenchmarkReference",
    "BidAskSpreadConfig",
    "PricingSpec",
    "QuoteSide",
]
