"""Typed output records used by portfolio aggregation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from fuggers_py._core.ids import EtfId, InstrumentId, PortfolioId
from fuggers_py._core.types import Date


def _to_decimal(value: object | None) -> Decimal | None:
    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_decimal_fields(instance: object, *names: str) -> None:
    for name in names:
        value = getattr(instance, name)
        coerced = _to_decimal(value)
        if coerced is not None:
            object.__setattr__(instance, name, coerced)


def _coerce_matching_alias_fields(instance: object, canonical_name: str, alias_name: str) -> None:
    canonical = getattr(instance, canonical_name)
    alias = getattr(instance, alias_name)
    if canonical is None and alias is None:
        return
    if canonical is None:
        object.__setattr__(instance, canonical_name, alias)
        return
    if alias is None:
        object.__setattr__(instance, alias_name, canonical)
        return
    if canonical != alias:
        raise ValueError(f"{canonical_name} and {alias_name} must match when both are provided.")


@dataclass(frozen=True, slots=True)
class BondQuoteOutput:
    """Bond pricing output with explicit unit-bearing fields."""

    instrument_id: InstrumentId | None = None
    pricing_path: str | None = None
    clean_price: Decimal | None = None
    dirty_price: Decimal | None = None
    accrued_interest: Decimal | None = None
    yield_to_maturity: Decimal | None = None
    yield_to_worst: Decimal | None = None
    current_yield: Decimal | None = None
    modified_duration: Decimal | None = None
    effective_duration: Decimal | None = None
    macaulay_duration: Decimal | None = None
    dv01: Decimal | None = None
    convexity: Decimal | None = None
    effective_convexity: Decimal | None = None
    key_rate_durations: dict[str, Decimal] = field(default_factory=dict)
    z_spread: Decimal | None = None
    g_spread: Decimal | None = None
    i_spread: Decimal | None = None
    oas: Decimal | None = None
    discount_margin: Decimal | None = None
    spread_duration: Decimal | None = None
    asset_swap_spread: Decimal | None = None
    benchmark_info: str | None = None
    option_value: Decimal | None = None
    projected_next_coupon: Decimal | None = None
    next_reset_date: Date | None = None
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    settlement_date: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    is_stale: bool = False
    quality_score: Decimal | None = None
    bid_price: Decimal | None = None
    mid_price: Decimal | None = None
    ask_price: Decimal | None = None
    ytc: Decimal | None = None
    pv01: Decimal | None = None
    cs01: Decimal | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(
            self,
            "clean_price",
            "dirty_price",
            "accrued_interest",
            "yield_to_maturity",
            "yield_to_worst",
            "current_yield",
            "modified_duration",
            "effective_duration",
            "macaulay_duration",
            "dv01",
            "convexity",
            "effective_convexity",
            "z_spread",
            "g_spread",
            "i_spread",
            "oas",
            "discount_margin",
            "spread_duration",
            "asset_swap_spread",
            "option_value",
            "projected_next_coupon",
            "quality_score",
            "bid_price",
            "mid_price",
            "ask_price",
            "ytc",
            "pv01",
            "cs01",
        )
        object.__setattr__(self, "key_rate_durations", {key: _to_decimal(value) for key, value in self.key_rate_durations.items()})
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        if self.pricing_path is not None:
            object.__setattr__(self, "pricing_path", self.pricing_path.strip())
        if self.benchmark_info is not None:
            object.__setattr__(self, "benchmark_info", self.benchmark_info.strip())
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "notes", tuple(self.notes))
        _coerce_matching_alias_fields(self, "dv01", "pv01")
        if self.mid_price is None and self.clean_price is not None:
            object.__setattr__(self, "mid_price", self.clean_price)


@dataclass(frozen=True, slots=True)
class EtfAnalyticsOutput:
    """ETF analytics output with explicit units and signed risk fields."""

    etf_id: EtfId | None = None
    gross_market_value: Decimal = Decimal(0)
    nav: Decimal | None = None
    inav: Decimal | None = None
    shares_outstanding: Decimal = Decimal(1)
    weighted_duration: Decimal | None = None
    weighted_convexity: Decimal | None = None
    aggregate_dv01: Decimal | None = None
    weighted_z_spread: Decimal | None = None
    weighted_g_spread: Decimal | None = None
    weighted_i_spread: Decimal | None = None
    holding_count: int = 0
    priced_count: int = 0
    fully_priced: bool = False
    settlement_date: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    is_stale: bool = False
    quality_score: Decimal | None = None
    bid_price: Decimal | None = None
    mid_price: Decimal | None = None
    ask_price: Decimal | None = None
    pv01: Decimal | None = None
    cs01: Decimal | None = None

    def __post_init__(self) -> None:
        if self.etf_id is not None:
            object.__setattr__(self, "etf_id", EtfId.parse(self.etf_id))
        _coerce_decimal_fields(
            self,
            "gross_market_value",
            "nav",
            "inav",
            "shares_outstanding",
            "weighted_duration",
            "weighted_convexity",
            "aggregate_dv01",
            "weighted_z_spread",
            "weighted_g_spread",
            "weighted_i_spread",
            "quality_score",
            "bid_price",
            "mid_price",
            "ask_price",
            "pv01",
            "cs01",
        )
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _coerce_matching_alias_fields(self, "aggregate_dv01", "pv01")
        if self.mid_price is None and self.nav is not None:
            object.__setattr__(self, "mid_price", self.nav)


@dataclass(frozen=True, slots=True)
class PortfolioAnalyticsOutput:
    """Portfolio analytics output with explicit units and signed risk fields."""

    portfolio_id: PortfolioId | None = None
    total_market_value: Decimal = Decimal(0)
    total_dirty_value: Decimal = Decimal(0)
    weighted_duration: Decimal | None = None
    weighted_convexity: Decimal | None = None
    aggregate_dv01: Decimal | None = None
    weighted_z_spread: Decimal | None = None
    weighted_g_spread: Decimal | None = None
    weighted_i_spread: Decimal | None = None
    key_rate_durations: dict[str, Decimal] = field(default_factory=dict)
    sector_breakdown: dict[str, Decimal] = field(default_factory=dict)
    rating_breakdown: dict[str, Decimal] = field(default_factory=dict)
    position_count: int = 0
    priced_count: int = 0
    fully_priced: bool = False
    settlement_date: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    is_stale: bool = False
    quality_score: Decimal | None = None
    pv01: Decimal | None = None
    cs01: Decimal | None = None

    def __post_init__(self) -> None:
        if self.portfolio_id is not None:
            object.__setattr__(self, "portfolio_id", PortfolioId.parse(self.portfolio_id))
        _coerce_decimal_fields(
            self,
            "total_market_value",
            "total_dirty_value",
            "weighted_duration",
            "weighted_convexity",
            "aggregate_dv01",
            "weighted_z_spread",
            "weighted_g_spread",
            "weighted_i_spread",
            "quality_score",
            "pv01",
            "cs01",
        )
        object.__setattr__(self, "key_rate_durations", {key: _to_decimal(value) for key, value in self.key_rate_durations.items()})
        object.__setattr__(self, "sector_breakdown", {key: _to_decimal(value) for key, value in self.sector_breakdown.items()})
        object.__setattr__(self, "rating_breakdown", {key: _to_decimal(value) for key, value in self.rating_breakdown.items()})
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _coerce_matching_alias_fields(self, "aggregate_dv01", "pv01")


__all__ = [
    "BondQuoteOutput",
    "EtfAnalyticsOutput",
    "PortfolioAnalyticsOutput",
]
