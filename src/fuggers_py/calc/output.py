"""Typed engine outputs and publisher contracts.

Shared calc outputs keep units explicit:

- bond ``clean_price`` and ``dirty_price`` stay in percent-of-par
- unsuffixed yields, rates, and spreads are raw decimals
- ``dv01`` is the canonical first-order rate-risk field
- ``pv01`` is kept only as a compatibility alias where it is still present

The dataclasses in this module are the public result records that ReadTheDocs
will surface for pricing, risk, and portfolio analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from fuggers_py.core.types import Date

from fuggers_py.core.ids import EtfId, InstrumentId, PortfolioId


def _to_decimal(value: object | None) -> Decimal | None:
    """Coerce a nullable output scalar to ``Decimal``."""
    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_decimal_fields(instance: object, *names: str) -> None:
    """Normalize named attributes on a dataclass-like instance to decimals."""
    for name in names:
        value = getattr(instance, name)
        coerced = _to_decimal(value)
        if coerced is not None:
            object.__setattr__(instance, name, coerced)


def _coerce_matching_alias_fields(instance: object, canonical_name: str, alias_name: str) -> None:
    """Backfill matching risk aliases and reject mismatched explicit inputs."""

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
    """Bond pricing output with explicit unit-bearing fields.

    ``clean_price`` and ``dirty_price`` are percent-of-par price levels,
    unsuffixed yield and spread fields are raw decimals, and ``dv01`` follows
    the shared signed convention. ``pv01`` is a compatibility alias of
    ``dv01``. Optional fields are left unset when the selected pricing path
    does not compute them.

    Attributes
    ----------
    instrument_id:
        Instrument identifier for the priced bond.
    pricing_path:
        Router label such as ``fixed``, ``callable``, ``floating_rate``, or
        ``tips_real_yield``.
    clean_price, dirty_price:
        Bond price levels in percent of par.
    accrued_interest:
        Accrued coupon amount in currency units.
    yield_to_maturity, yield_to_worst, current_yield, ytc:
        Yield measures as raw decimals.
    modified_duration, effective_duration, macaulay_duration, dv01, convexity,
    effective_convexity:
        First- and second-order risk outputs. ``dv01`` is per 100 face and
        signed positive when value rises as yield falls.
    z_spread, g_spread, i_spread, oas, discount_margin, spread_duration,
    asset_swap_spread:
        Optional spread and spread-risk fields, all as raw decimals.
    key_rate_durations:
        Tenor-keyed partial DV01 profile.
    option_value, projected_next_coupon, next_reset_date:
        Path-specific fields used by callable, inflation-linked, and
        floating-rate pricing paths.
    bid_price, mid_price, ask_price:
        Optional side-specific price views in percent of par.
    warnings, notes:
        Extra path-specific messages for downstream consumers.
    """

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
        object.__setattr__(
            self,
            "key_rate_durations",
            {key: _to_decimal(value) for key, value in self.key_rate_durations.items()},
        )
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
class SwapQuoteOutput:
    """Swap pricing output with raw-decimal rates and signed DV01.

    The record captures the par rate, PV decomposition, annuity, and signed
    rate risk for fixed-float swaps and OIS instruments. ``pv01`` is a
    compatibility alias of ``dv01``.

    Attributes
    ----------
    par_rate:
        Fair fixed rate as a raw decimal.
    present_value:
        Signed swap PV in currency units.
    fixed_leg_pv, floating_leg_pv:
        Signed leg PV contributions in currency units.
    annuity:
        Fixed-leg annuity used by the pricer.
    dv01:
        Signed first-order PV change for a 1 bp move.
    """

    instrument_id: InstrumentId | None = None
    pricing_path: str | None = None
    par_rate: Decimal | None = None
    present_value: Decimal | None = None
    fixed_leg_pv: Decimal | None = None
    floating_leg_pv: Decimal | None = None
    annuity: Decimal | None = None
    dv01: Decimal | None = None
    pv01: Decimal | None = None
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    settlement_date: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    is_stale: bool = False
    quality_score: Decimal | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(
            self,
            "par_rate",
            "present_value",
            "fixed_leg_pv",
            "floating_leg_pv",
            "annuity",
            "dv01",
            "pv01",
            "quality_score",
        )
        if self.pricing_path is not None:
            object.__setattr__(self, "pricing_path", self.pricing_path.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "notes", tuple(self.notes))
        _coerce_matching_alias_fields(self, "dv01", "pv01")


@dataclass(frozen=True, slots=True)
class BasisSwapQuoteOutput:
    """Basis-swap pricing output with raw decimals and signed DV01.

    The basis spread is quoted as a raw decimal. The record preserves the pay
    and receive leg PVs so callers can inspect the leg contribution separately.
    ``pv01`` is a compatibility alias of ``dv01``.

    Attributes
    ----------
    basis_spread:
        Fair basis spread as a raw decimal.
    present_value:
        Signed total PV in currency units.
    pay_leg_pv, receive_leg_pv:
        Signed leg PV contributions in currency units.
    dv01:
        Signed first-order PV change for a 1 bp move.
    """

    instrument_id: InstrumentId | None = None
    pricing_path: str | None = None
    basis_spread: Decimal | None = None
    present_value: Decimal | None = None
    pay_leg_pv: Decimal | None = None
    receive_leg_pv: Decimal | None = None
    dv01: Decimal | None = None
    pv01: Decimal | None = None
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    settlement_date: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    is_stale: bool = False
    quality_score: Decimal | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(
            self,
            "basis_spread",
            "present_value",
            "pay_leg_pv",
            "receive_leg_pv",
            "dv01",
            "pv01",
            "quality_score",
        )
        if self.pricing_path is not None:
            object.__setattr__(self, "pricing_path", self.pricing_path.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "notes", tuple(self.notes))
        _coerce_matching_alias_fields(self, "dv01", "pv01")


@dataclass(frozen=True, slots=True)
class FutureQuoteOutput:
    """Future pricing output with price levels and signed DV01.

    The record carries the futures price, implied repo, basis measures, and the
    cheapest-to-deliver reference instrument when one is resolved. ``pv01`` is
    a compatibility alias of ``dv01``.

    Attributes
    ----------
    futures_price, fair_value:
        Futures price levels in the contract quote convention.
    implied_repo_rate:
        Implied repo as a raw decimal.
    net_basis, gross_basis:
        Basis measures in the pricer's raw output units.
    conversion_factor:
        Delivery conversion factor for the CTD bond.
    ctd_instrument_id:
        Cheapest-to-deliver bond when the pricer resolved one.
    dv01:
        Signed first-order PV change for a 1 bp move.
    """

    instrument_id: InstrumentId | None = None
    pricing_path: str | None = None
    futures_price: Decimal | None = None
    fair_value: Decimal | None = None
    implied_repo_rate: Decimal | None = None
    net_basis: Decimal | None = None
    gross_basis: Decimal | None = None
    conversion_factor: Decimal | None = None
    dv01: Decimal | None = None
    pv01: Decimal | None = None
    ctd_instrument_id: InstrumentId | None = None
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    settlement_date: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    is_stale: bool = False
    quality_score: Decimal | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.ctd_instrument_id is not None:
            object.__setattr__(self, "ctd_instrument_id", InstrumentId.parse(self.ctd_instrument_id))
        _coerce_decimal_fields(
            self,
            "futures_price",
            "fair_value",
            "implied_repo_rate",
            "net_basis",
            "gross_basis",
            "conversion_factor",
            "dv01",
            "pv01",
            "quality_score",
        )
        if self.pricing_path is not None:
            object.__setattr__(self, "pricing_path", self.pricing_path.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "notes", tuple(self.notes))
        _coerce_matching_alias_fields(self, "dv01", "pv01")


@dataclass(frozen=True, slots=True)
class RoutedFraPricingResult:
    """Structured FRA pricing output with signed DV01.

    The record keeps the forward rate, discount factor, year fraction, and the
    rate-sensitivity fields used by the calc layer. ``pv01`` is a
    compatibility alias of ``dv01``.

    Attributes
    ----------
    forward_rate:
        Fair FRA rate as a raw decimal.
    present_value:
        Signed FRA PV in currency units.
    year_fraction:
        Accrual fraction used by the FRA cash-settlement formula.
    discount_factor:
        Discount factor used for settlement.
    dv01:
        Signed first-order PV change for a 1 bp move.
    """

    instrument_id: InstrumentId | None = None
    pricing_path: str | None = None
    forward_rate: Decimal | None = None
    present_value: Decimal | None = None
    year_fraction: Decimal | None = None
    discount_factor: Decimal | None = None
    dv01: Decimal | None = None
    pv01: Decimal | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(
            self,
            "forward_rate",
            "present_value",
            "year_fraction",
            "discount_factor",
            "dv01",
            "pv01",
        )
        if self.pricing_path is not None:
            object.__setattr__(self, "pricing_path", self.pricing_path.strip())
        _coerce_matching_alias_fields(self, "dv01", "pv01")


@dataclass(frozen=True, slots=True)
class CdsQuoteOutput:
    """CDS pricing output with spread, upfront, and recovery fields.

    Par spread, upfront, PV, and PV01/CS01 are stored as raw decimals. Recovery
    rate is also kept as a raw decimal rather than a percentage.

    Attributes
    ----------
    par_spread:
        Fair CDS spread as a raw decimal.
    upfront:
        Fair upfront amount as a fraction of notional.
    present_value:
        Signed CDS PV in currency units.
    pv01:
        Premium-leg PV01 style sensitivity used by the CDS pricer.
    cs01:
        Signed spread sensitivity in currency units per 1 bp.
    risky_duration:
        Premium-leg risky duration style measure from the pricer.
    recovery_rate:
        Assumed recovery rate as a raw decimal.
    """

    instrument_id: InstrumentId | None = None
    pricing_path: str | None = None
    par_spread: Decimal | None = None
    upfront: Decimal | None = None
    present_value: Decimal | None = None
    cs01: Decimal | None = None
    pv01: Decimal | None = None
    risky_duration: Decimal | None = None
    recovery_rate: Decimal | None = None
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    settlement_date: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    is_stale: bool = False
    quality_score: Decimal | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(
            self,
            "par_spread",
            "upfront",
            "present_value",
            "cs01",
            "pv01",
            "risky_duration",
            "recovery_rate",
            "quality_score",
        )
        if self.pricing_path is not None:
            object.__setattr__(self, "pricing_path", self.pricing_path.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "notes", tuple(self.notes))


@dataclass(frozen=True, slots=True)
class RvSignalOutput:
    """Relative-value signal output with normalized direction metadata.

    Direction is normalized to lowercase and the record keeps the score,
    z-score, bucket, and horizon metadata used for relative-value screening.
    """

    instrument_id: InstrumentId | None = None
    signal_name: str | None = None
    score: Decimal | None = None
    z_score: Decimal | None = None
    direction: str | None = None
    bucket: str | None = None
    horizon: str | None = None
    timestamp: datetime | None = None
    source: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(self, "score", "z_score")
        if self.signal_name is not None:
            object.__setattr__(self, "signal_name", self.signal_name.strip())
        if self.direction is not None:
            object.__setattr__(self, "direction", self.direction.strip().lower())
        if self.bucket is not None:
            object.__setattr__(self, "bucket", self.bucket.strip())
        if self.horizon is not None:
            object.__setattr__(self, "horizon", self.horizon.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "notes", tuple(self.notes))


@dataclass(frozen=True, slots=True)
class EtfAnalyticsOutput:
    """ETF analytics output with explicit units and signed risk fields.

    Market value, NAV, holdings-weighted risk, and spread metrics are stored as
    raw decimals. ``aggregate_dv01`` is the canonical field. ``pv01`` is a
    compatibility alias.

    Attributes
    ----------
    gross_market_value, nav, inav:
        ETF valuation fields in currency units.
    shares_outstanding:
        Share count used by per-share calculations.
    weighted_duration, weighted_convexity:
        Holdings-weighted risk measures.
    aggregate_dv01:
        Canonical ETF DV01 in currency units per 1 bp.
    weighted_z_spread, weighted_g_spread, weighted_i_spread:
        Holdings-weighted spread measures as raw decimals.
    bid_price, mid_price, ask_price:
        Optional ETF quote levels.
    cs01:
        Aggregate spread sensitivity in currency units per 1 bp.
    """

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
    """Portfolio analytics output with explicit units and signed risk fields.

    The record keeps market value, dirty value, weighted risk, and the optional
    key-rate, sector, and rating breakdowns used by portfolio analytics.
    ``aggregate_dv01`` is the canonical field. ``pv01`` is a compatibility
    alias.

    Attributes
    ----------
    total_market_value, total_dirty_value:
        Portfolio valuation totals in currency units.
    weighted_duration, weighted_convexity:
        Portfolio-level weighted interest-rate risk measures.
    aggregate_dv01:
        Canonical portfolio DV01 in currency units per 1 bp.
    weighted_z_spread, weighted_g_spread, weighted_i_spread:
        Portfolio-level spread measures as raw decimals.
    key_rate_durations:
        Tenor-keyed partial DV01 profile.
    sector_breakdown, rating_breakdown:
        Optional grouped analytics maps.
    position_count, priced_count, fully_priced:
        Coverage diagnostics for downstream reporting.
    cs01:
        Aggregate spread sensitivity in currency units per 1 bp.
    """

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
        object.__setattr__(
            self,
            "key_rate_durations",
            {key: _to_decimal(value) for key, value in self.key_rate_durations.items()},
        )
        object.__setattr__(
            self,
            "sector_breakdown",
            {key: _to_decimal(value) for key, value in self.sector_breakdown.items()},
        )
        object.__setattr__(
            self,
            "rating_breakdown",
            {key: _to_decimal(value) for key, value in self.rating_breakdown.items()},
        )
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _coerce_matching_alias_fields(self, "aggregate_dv01", "pv01")


@dataclass(frozen=True, slots=True)
class RepoPricingResult:
    """Structured repo pricing output with raw-decimal rate fields.

    The record keeps collateral value, haircut, cash lent, accrued interest,
    and repo-curve diagnostics for funding workflows.
    """

    collateral_value: Decimal
    haircut_amount: Decimal
    cash_lent: Decimal
    year_fraction: Decimal
    interest_amount: Decimal
    repurchase_amount: Decimal
    curve_zero_rate: Decimal | None = None
    forward_rate: Decimal | None = None
    funding_spread: Decimal | None = None

    def __post_init__(self) -> None:
        _coerce_decimal_fields(
            self,
            "collateral_value",
            "haircut_amount",
            "cash_lent",
            "year_fraction",
            "interest_amount",
            "repurchase_amount",
            "curve_zero_rate",
            "forward_rate",
            "funding_spread",
        )


AnalyticsOutput = (
    BondQuoteOutput
    | SwapQuoteOutput
    | BasisSwapQuoteOutput
    | FutureQuoteOutput
    | RoutedFraPricingResult
    | CdsQuoteOutput
    | RvSignalOutput
    | EtfAnalyticsOutput
    | PortfolioAnalyticsOutput
    | RepoPricingResult
)


@runtime_checkable
class QuotePublisher(Protocol):
    """Protocol for publishing bond quote outputs."""

    def publish_quote(self, quote: BondQuoteOutput) -> None:
        ...


@runtime_checkable
class EtfPublisher(Protocol):
    """Protocol for publishing ETF analytics outputs."""

    def publish_etf(self, analytics: EtfAnalyticsOutput) -> None:
        ...


@runtime_checkable
class AnalyticsPublisher(Protocol):
    """Protocol for publishing any supported analytics output."""

    def publish_analytics(self, analytics: AnalyticsOutput) -> None:
        ...


@runtime_checkable
class AlertPublisher(Protocol):
    """Protocol for publishing alert messages."""

    def publish_alert(self, message: str, *, severity: str = "info") -> None:
        ...


@dataclass(slots=True)
class OutputPublisher:
    """Composite publisher that delegates to optional channel publishers.

    The helper keeps the publish path optional: if a dedicated channel is not
    configured, the corresponding publish method becomes a no-op.
    """

    quote_publisher: QuotePublisher | None = None
    etf_publisher: EtfPublisher | None = None
    analytics_publisher: AnalyticsPublisher | None = None
    alert_publisher: AlertPublisher | None = None

    def publish_quote(self, quote: BondQuoteOutput) -> None:
        """Publish a bond quote when a quote publisher is configured."""
        if self.quote_publisher is not None:
            self.quote_publisher.publish_quote(quote)

    def publish_etf(self, analytics: EtfAnalyticsOutput) -> None:
        """Publish ETF analytics when an ETF publisher is configured."""
        if self.etf_publisher is not None:
            self.etf_publisher.publish_etf(analytics)

    def publish_analytics(self, analytics: AnalyticsOutput) -> None:
        """Publish analytics or fall back to the specific channel handlers."""
        if self.analytics_publisher is not None:
            self.analytics_publisher.publish_analytics(analytics)
            return
        if isinstance(analytics, BondQuoteOutput):
            self.publish_quote(analytics)
        elif isinstance(analytics, EtfAnalyticsOutput):
            self.publish_etf(analytics)

    def publish_alert(self, message: str, *, severity: str = "info") -> None:
        """Publish an alert when an alert publisher is configured."""
        if self.alert_publisher is not None:
            self.alert_publisher.publish_alert(message, severity=severity)


__all__ = [
    "AlertPublisher",
    "AnalyticsOutput",
    "AnalyticsPublisher",
    "BasisSwapQuoteOutput",
    "BondQuoteOutput",
    "CdsQuoteOutput",
    "EtfAnalyticsOutput",
    "EtfPublisher",
    "FutureQuoteOutput",
    "OutputPublisher",
    "PortfolioAnalyticsOutput",
    "QuotePublisher",
    "RepoPricingResult",
    "RoutedFraPricingResult",
    "RvSignalOutput",
    "SwapQuoteOutput",
]
