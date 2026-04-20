"""Holding and analytics types.

Holdings keep the bond instrument, size, valuation inputs, and classification
metadata together so portfolio analytics can derive clean and dirty values
without guessing at settlement, currency, or market-price conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py.bonds import Bond
from fuggers_py.bonds import RatingInfo, SectorInfo, SeniorityInfo
from fuggers_py._core.types import Currency, Price

from .classification import Classification


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, Price):
        return value.as_percentage()
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class HoldingAnalytics:
    """Per-holding analytics expressed in currency and raw-decimal units.

    The currency fields are value terms for the individual holding. Yield,
    spread, duration, convexity, and key-rate fields use the library's raw
    decimal convention unless the field name explicitly says otherwise.
    """

    name: str
    market_value: Decimal
    dirty_value: Decimal
    clean_value: Decimal
    accrued_value: Decimal
    duration: Decimal
    convexity: Decimal
    dv01: Decimal
    ytm: Decimal | None = None
    ytw: Decimal | None = None
    ytc: Decimal | None = None
    current_yield: Decimal | None = None
    best_yield: Decimal | None = None
    z_spread: Decimal | None = None
    oas: Decimal | None = None
    g_spread: Decimal | None = None
    i_spread: Decimal | None = None
    asw: Decimal | None = None
    best_spread: Decimal | None = None
    spread_duration: Decimal | None = None
    cs01: Decimal | None = None
    modified_duration: Decimal | None = None
    effective_duration: Decimal | None = None
    macaulay_duration: Decimal | None = None
    effective_convexity: Decimal | None = None
    key_rate_profile: dict[str, Decimal] = field(default_factory=dict)
    liquidity_score: Decimal | None = None
    weighted_average_life: Decimal | None = None
    coupon: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Holding:
    """A bond holding with optional valuation and classification metadata.

    The holding stores the instrument, position size, optional pricing inputs,
    and optional classification metadata used for portfolio aggregation. When a
    clean price is present, market value is derived from the price and quantity
    unless an explicit market value is provided.
    """

    instrument: Bond
    quantity: Decimal = Decimal(1)
    clean_price: Price | Decimal | None = None
    market_value: Decimal | None = None
    accrued_interest: Decimal | None = None
    analytics: HoldingAnalytics | None = None
    label: str | None = None
    id: str | None = None
    classification: Classification | None = None
    rating_info: RatingInfo | None = None
    sector_info: SectorInfo | None = None
    seniority_info: SeniorityInfo | None = None
    liquidity_score: Decimal | None = None
    custom_fields: dict[str, str] = field(default_factory=dict)
    fx_rate: Decimal = Decimal(1)

    def __post_init__(self) -> None:
        """Normalize numeric inputs to :class:`~decimal.Decimal`.

        This keeps downstream portfolio aggregation consistent regardless of
        whether callers passed `Decimal`, `Price`, or other numeric-like
        inputs.
        """

        object.__setattr__(self, "quantity", _to_decimal(self.quantity))
        if self.market_value is not None:
            object.__setattr__(self, "market_value", _to_decimal(self.market_value))
        if self.accrued_interest is not None:
            object.__setattr__(self, "accrued_interest", _to_decimal(self.accrued_interest))
        if self.liquidity_score is not None:
            object.__setattr__(self, "liquidity_score", _to_decimal(self.liquidity_score))
        object.__setattr__(self, "fx_rate", _to_decimal(self.fx_rate))

    @property
    def par_amount(self) -> Decimal:
        """Return the par amount carried by the holding."""

        return self.quantity

    @property
    def market_price(self) -> Decimal | None:
        """Return the clean market price as a percent-of-par value."""

        if self.clean_price is None:
            return None
        return _to_decimal(self.clean_price)

    @property
    def currency(self) -> Currency:
        """Return the holding currency, preferring explicit classification."""

        if self.classification is not None and self.classification.currency is not None:
            return self.classification.currency
        return self.instrument.currency()

    def name(self) -> str:
        """Return a stable display name for the holding."""

        if self.label is not None:
            return self.label
        if self.id is not None:
            return self.id
        identifiers = self.instrument.identifiers()
        return identifiers.isin.value if identifiers.isin is not None else self.instrument.__class__.__name__

    @property
    def market_value_amount(self) -> Decimal:
        """Return the clean market value in currency units.

        If an explicit market value is present it is used directly; otherwise
        the clean price is multiplied by the par amount.
        """

        if self.market_value is not None:
            return self.market_value
        if self.clean_price is None:
            return Decimal(0)
        return _to_decimal(self.clean_price) * self.quantity

    @property
    def dirty_market_value(self) -> Decimal:
        """Return the dirty market value in currency units.

        Accrued interest is added on a par-amount basis so the result is a
        dirty value consistent with dirty-PV aggregation.
        """

        accrued = self.accrued_interest or Decimal(0)
        return self.market_value_amount + (accrued * self.quantity)

    @property
    def base_currency_value(self) -> Decimal:
        """Return the clean market value translated by ``fx_rate``."""

        return self.market_value_amount * self.fx_rate

    def weight_in_portfolio(self, total_market_value: Decimal) -> Decimal:
        """Return the clean-value weight of the holding within a portfolio."""

        if total_market_value == 0:
            return Decimal(0)
        return self.market_value_amount / total_market_value


@dataclass(slots=True)
class HoldingBuilder:
    """Mutable builder for :class:`Holding` instances."""

    instrument: Bond | None = None
    quantity: Decimal = Decimal(1)
    clean_price: Price | Decimal | None = None
    market_value: Decimal | None = None
    accrued_interest: Decimal | None = None
    analytics: HoldingAnalytics | None = None
    label: str | None = None
    id: str | None = None
    classification: Classification | None = None
    rating_info: RatingInfo | None = None
    sector_info: SectorInfo | None = None
    seniority_info: SeniorityInfo | None = None
    liquidity_score: Decimal | None = None
    custom_fields: dict[str, str] = field(default_factory=dict)
    fx_rate: Decimal = Decimal(1)

    def with_instrument(self, instrument: Bond) -> "HoldingBuilder":
        """Set the underlying instrument."""

        self.instrument = instrument
        return self

    def with_quantity(self, quantity: object) -> "HoldingBuilder":
        """Set the par amount or share quantity."""

        self.quantity = _to_decimal(quantity)
        return self

    def with_par_amount(self, par_amount: object) -> "HoldingBuilder":
        """Compatibility alias for :meth:`with_quantity`."""

        return self.with_quantity(par_amount)

    def with_clean_price(self, clean_price: Price | Decimal) -> "HoldingBuilder":
        """Set the clean price as a percent-of-par value."""

        self.clean_price = clean_price
        return self

    def with_market_price(self, market_price: Price | Decimal) -> "HoldingBuilder":
        """Compatibility alias for :meth:`with_clean_price`."""

        return self.with_clean_price(market_price)

    def with_market_value(self, market_value: object) -> "HoldingBuilder":
        """Set the clean market value in currency units."""

        self.market_value = _to_decimal(market_value)
        return self

    def with_accrued_interest(self, accrued_interest: object) -> "HoldingBuilder":
        """Set accrued interest in currency units."""

        self.accrued_interest = _to_decimal(accrued_interest)
        return self

    def with_analytics(self, analytics: HoldingAnalytics) -> "HoldingBuilder":
        """Attach precomputed analytics."""

        self.analytics = analytics
        return self

    def with_label(self, label: str) -> "HoldingBuilder":
        """Set the display label."""

        self.label = label
        return self

    def with_id(self, value: str) -> "HoldingBuilder":
        """Set the stable identifier used as a fallback name."""

        self.id = value
        return self

    def with_classification(self, classification: Classification) -> "HoldingBuilder":
        """Attach classification metadata."""

        self.classification = classification
        return self

    def with_rating_info(self, rating_info: RatingInfo) -> "HoldingBuilder":
        """Attach rating metadata."""

        self.rating_info = rating_info
        return self

    def with_sector_info(self, sector_info: SectorInfo) -> "HoldingBuilder":
        """Attach sector metadata."""

        self.sector_info = sector_info
        return self

    def with_seniority_info(self, seniority_info: SeniorityInfo) -> "HoldingBuilder":
        """Attach seniority metadata."""

        self.seniority_info = seniority_info
        return self

    def with_liquidity_score(self, liquidity_score: object) -> "HoldingBuilder":
        """Set the liquidity score as a raw decimal."""

        self.liquidity_score = _to_decimal(liquidity_score)
        return self

    def with_fx_rate(self, fx_rate: object) -> "HoldingBuilder":
        """Set the base-currency FX conversion rate."""

        self.fx_rate = _to_decimal(fx_rate)
        return self

    def build(self) -> Holding:
        """Create the immutable holding.

        Raises
        ------
        ValueError
            If no instrument has been set.
        """

        if self.instrument is None:
            raise ValueError("HoldingBuilder requires an instrument.")
        return Holding(
            instrument=self.instrument,
            quantity=self.quantity,
            clean_price=self.clean_price,
            market_value=self.market_value,
            accrued_interest=self.accrued_interest,
            analytics=self.analytics,
            label=self.label,
            id=self.id,
            classification=self.classification,
            rating_info=self.rating_info,
            sector_info=self.sector_info,
            seniority_info=self.seniority_info,
            liquidity_score=self.liquidity_score,
            custom_fields=dict(self.custom_fields),
            fx_rate=self.fx_rate,
        )


Position = Holding
PositionAnalytics = HoldingAnalytics


__all__ = [
    "Holding",
    "HoldingAnalytics",
    "HoldingBuilder",
    "Position",
    "PositionAnalytics",
]
