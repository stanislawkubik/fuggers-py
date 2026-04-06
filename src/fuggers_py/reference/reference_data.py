"""Reference-data records for research workflows.

Reference records normalize typed identifiers and free-form descriptors while
preserving raw decimal fields such as spreads, coupons, recovery rates, and
haircuts. These objects define the contract between source feeds and bond,
swap, repo, CDS, and ETF construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum
from typing import Protocol, runtime_checkable

from fuggers_py.products.bonds.instruments import CallableBondBuilder, FixedBondBuilder, FloatingRateNoteBuilder, ZeroCouponBond
from fuggers_py.reference.bonds.types import RateIndex, YieldCalculationRules
from fuggers_py.core.types import Currency, Date, Frequency

from fuggers_py.core.ids import EtfId, InstrumentId, YearMonth
from fuggers_py.market.snapshot import EtfHolding


def _to_decimal(value: object) -> Decimal:
    """Coerce a reference-data scalar to ``Decimal``."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_frequency(value: Frequency | str) -> Frequency:
    """Normalize a frequency descriptor or enum member."""
    if isinstance(value, Frequency):
        return value
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "ANNUAL": Frequency.ANNUAL,
        "YEARLY": Frequency.ANNUAL,
        "SEMIANNUAL": Frequency.SEMI_ANNUAL,
        "SEMI_ANNUAL": Frequency.SEMI_ANNUAL,
        "SEMI": Frequency.SEMI_ANNUAL,
        "QUARTERLY": Frequency.QUARTERLY,
        "QUARTER": Frequency.QUARTERLY,
        "MONTHLY": Frequency.MONTHLY,
        "MONTH": Frequency.MONTHLY,
        "ZERO": Frequency.ZERO,
    }
    if normalized in aliases:
        return aliases[normalized]
    return Frequency[normalized]


class BondType(str, Enum):
    """Supported bond reference types used to select instrument builders."""

    FIXED_RATE = "FIXED_RATE"
    ZERO_COUPON = "ZERO_COUPON"
    CALLABLE = "CALLABLE"
    PUTTABLE = "PUTTABLE"
    CALLABLE_AND_PUTTABLE = "CALLABLE_AND_PUTTABLE"
    FLOATING_RATE = "FLOATING_RATE"


class IssuerType(str, Enum):
    """Normalized issuer categories used for default yield rules."""

    SOVEREIGN = "SOVEREIGN"
    AGENCY = "AGENCY"
    CORPORATE = "CORPORATE"
    MUNICIPAL = "MUNICIPAL"
    SUPRANATIONAL = "SUPRANATIONAL"
    ETF = "ETF"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class CallScheduleEntry:
    """Single callable or puttable exercise point.

    Parameters
    ----------
    exercise_date:
        Exercise date in the bond's schedule, stored as a calendar date.
    price:
        Exercise price as a raw decimal amount, typically per 100 notional.
    """

    exercise_date: Date
    price: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", _to_decimal(self.price))


@dataclass(frozen=True, slots=True)
class FloatingRateTerms:
    """Floating-rate note terms with raw decimal rate fields.

    The index name is normalized to uppercase and the spread, caps, floors,
    and current reference rate are stored as raw decimals.
    """

    index_name: str
    spread: Decimal
    reset_frequency: Frequency
    current_reference_rate: Decimal | None = None
    cap_rate: Decimal | None = None
    floor_rate: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(self, "spread", _to_decimal(self.spread))
        if self.current_reference_rate is not None:
            object.__setattr__(self, "current_reference_rate", _to_decimal(self.current_reference_rate))
        if self.cap_rate is not None:
            object.__setattr__(self, "cap_rate", _to_decimal(self.cap_rate))
        if self.floor_rate is not None:
            object.__setattr__(self, "floor_rate", _to_decimal(self.floor_rate))

    def rate_index(self) -> RateIndex:
        """Map the normalized index name to the bond-layer rate index."""
        return RateIndex[self.index_name]


@dataclass(frozen=True, slots=True)
class BondReferenceData:
    """Bond reference record used to construct bond instruments.

    The record normalizes identifiers, sorts optional schedules, and uses the
    issuer type to infer default yield rules when none are supplied. Coupon
    rate, notional, and amount fields are stored as raw decimals.
    """

    instrument_id: InstrumentId
    bond_type: BondType
    issuer_type: IssuerType
    issue_date: Date
    maturity_date: Date
    currency: Currency = Currency.USD
    notional: Decimal = Decimal(100)
    coupon_rate: Decimal | None = None
    frequency: Frequency | None = None
    yield_rules: YieldCalculationRules | None = None
    floating_rate_terms: FloatingRateTerms | None = None
    call_schedule: tuple[CallScheduleEntry, ...] = field(default_factory=tuple)
    put_schedule: tuple[CallScheduleEntry, ...] = field(default_factory=tuple)
    issuer_name: str | None = None
    sector: str | None = None
    rating: str | None = None
    amount_outstanding: Decimal | None = None
    benchmark_flag: bool | None = None
    futures_deliverable_flags: tuple[str, ...] = field(default_factory=tuple)
    liquidity_score: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        if self.coupon_rate is not None:
            object.__setattr__(self, "coupon_rate", _to_decimal(self.coupon_rate))
        if self.amount_outstanding is not None:
            object.__setattr__(self, "amount_outstanding", _to_decimal(self.amount_outstanding))
        if self.liquidity_score is not None:
            object.__setattr__(self, "liquidity_score", _to_decimal(self.liquidity_score))
        ordered_calls = tuple(sorted(self.call_schedule, key=lambda item: item.exercise_date))
        ordered_puts = tuple(sorted(self.put_schedule, key=lambda item: item.exercise_date))
        object.__setattr__(self, "call_schedule", ordered_calls)
        object.__setattr__(self, "put_schedule", ordered_puts)
        object.__setattr__(
            self,
            "futures_deliverable_flags",
            tuple(str(item).strip().upper() for item in self.futures_deliverable_flags if str(item).strip()),
        )
        if self.issuer_name is not None:
            object.__setattr__(self, "issuer_name", self.issuer_name.strip())
        if self.sector is not None:
            object.__setattr__(self, "sector", self.sector.strip())
        if self.rating is not None:
            object.__setattr__(self, "rating", self.rating.strip())
        if self.amount_outstanding is not None and self.amount_outstanding < Decimal(0):
            raise ValueError("BondReferenceData amount_outstanding must be non-negative when supplied.")
        if self.liquidity_score is not None and self.liquidity_score < Decimal(0):
            raise ValueError("BondReferenceData liquidity_score must be non-negative when supplied.")

    def to_instrument(self):
        """Convert the reference record into a bond instrument instance.

        Fixed-rate and zero-coupon records are converted directly. Callable and
        puttable records use the sorted embedded exercise schedules, and
        floating-rate records require ``floating_rate_terms``.
        """
        if self.bond_type is BondType.ZERO_COUPON:
            return ZeroCouponBond(
                _issue_date=self.issue_date,
                _maturity_date=self.maturity_date,
                _currency=self.currency,
                _notional=self.notional,
                _rules=self._yield_rules(self.frequency or Frequency.ANNUAL),
                instrument_id=self.instrument_id,
            )

        if self.bond_type is BondType.FLOATING_RATE:
            if self.floating_rate_terms is None:
                raise ValueError("Floating-rate reference data requires floating_rate_terms.")
            terms = self.floating_rate_terms
            return (
                FloatingRateNoteBuilder.new()
                .with_issue_date(self.issue_date)
                .with_maturity_date(self.maturity_date)
                .with_index(terms.rate_index())
                .with_quoted_spread(terms.spread)
                .with_frequency(terms.reset_frequency)
                .with_currency(self.currency)
                .with_notional(self.notional)
                .with_instrument_id(self.instrument_id)
                .with_rules(self._yield_rules(terms.reset_frequency))
                .with_current_reference_rate(terms.current_reference_rate or Decimal(0))
                .build()
            )

        if self.coupon_rate is None:
            raise ValueError("Fixed-rate style reference data requires coupon_rate.")
        frequency = self.frequency or Frequency.SEMI_ANNUAL
        base_bond = (
            FixedBondBuilder.new()
            .with_issue_date(self.issue_date)
            .with_maturity_date(self.maturity_date)
            .with_coupon_rate(self.coupon_rate)
            .with_frequency(frequency)
            .with_currency(self.currency)
            .with_notional(self.notional)
            .with_instrument_id(self.instrument_id)
            .with_rules(self._yield_rules(frequency))
            .build()
        )
        if self.bond_type is BondType.FIXED_RATE:
            return base_bond

        builder = CallableBondBuilder.new().with_base_bond(base_bond)
        for entry in self.call_schedule:
            builder = builder.add_call(call_date=entry.exercise_date, call_price=entry.price)
        for entry in self.put_schedule:
            builder = builder.add_put(put_date=entry.exercise_date, put_price=entry.price)
        return builder.build()

    def _yield_rules(self, frequency: Frequency) -> YieldCalculationRules:
        """Resolve yield rules using explicit settings or issuer defaults.

        When a convention bundle is supplied, the coupon frequency is aligned to
        the requested bond frequency before instrument construction.
        """
        if self.yield_rules is not None:
            if self.yield_rules.frequency is frequency:
                return self.yield_rules
            return replace(self.yield_rules, frequency=frequency)
        if self.issuer_type is IssuerType.CORPORATE:
            rules = YieldCalculationRules.us_corporate()
        else:
            rules = YieldCalculationRules.us_treasury()
        if rules.frequency is frequency:
            return rules
        return replace(rules, frequency=frequency)


@dataclass(frozen=True, slots=True)
class BondFutureReferenceData:
    """Reference metadata for a bond futures contract.

    The record keeps delivery and basket metadata separate from pricing logic
    and normalizes the underlying basket into parsed instrument ids.
    """

    instrument_id: InstrumentId
    currency: Currency = Currency.USD
    delivery_month: YearMonth | None = None
    contract_size: Decimal | None = None
    tick_size: Decimal | None = None
    exchange: str | None = None
    first_delivery_date: Date | None = None
    last_delivery_date: Date | None = None
    final_delivery_date: Date | None = None
    standard_coupon_rate: Decimal | None = None
    coupon_frequency: Frequency | str | None = None
    underlying_basket: tuple[InstrumentId, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.delivery_month is not None:
            object.__setattr__(self, "delivery_month", YearMonth.parse(self.delivery_month))
        if self.exchange is not None:
            object.__setattr__(self, "exchange", self.exchange.strip().upper())
        object.__setattr__(self, "underlying_basket", tuple(InstrumentId.parse(item) for item in self.underlying_basket))
        if self.contract_size is not None:
            object.__setattr__(self, "contract_size", _to_decimal(self.contract_size))
        if self.tick_size is not None:
            object.__setattr__(self, "tick_size", _to_decimal(self.tick_size))
        if self.standard_coupon_rate is not None:
            object.__setattr__(self, "standard_coupon_rate", _to_decimal(self.standard_coupon_rate))
        if self.coupon_frequency is not None:
            object.__setattr__(self, "coupon_frequency", _coerce_frequency(self.coupon_frequency))
        if self.first_delivery_date is not None and self.last_delivery_date is not None:
            if self.last_delivery_date < self.first_delivery_date:
                raise ValueError("BondFutureReferenceData requires last_delivery_date on or after first_delivery_date.")
        if self.final_delivery_date is not None and self.last_delivery_date is not None:
            if self.final_delivery_date < self.last_delivery_date:
                raise ValueError("BondFutureReferenceData requires final_delivery_date on or after last_delivery_date.")


BondFutureContractReference = BondFutureReferenceData


FutureReferenceData = BondFutureReferenceData


@dataclass(frozen=True, slots=True)
class DeliverableBondReference:
    """Deliverable bond metadata for a bond futures basket.

    ``published_conversion_factor`` records the source-provided factor and is
    distinct from any model-implied conversion factor.
    """

    instrument_id: InstrumentId
    issue_date: Date
    maturity_date: Date
    coupon_rate: Decimal
    currency: Currency = Currency.USD
    frequency: Frequency | str = Frequency.SEMI_ANNUAL
    notional: Decimal = Decimal(100)
    yield_rules: YieldCalculationRules | None = None
    published_conversion_factor: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "coupon_rate", _to_decimal(self.coupon_rate))
        object.__setattr__(self, "frequency", _coerce_frequency(self.frequency))
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        if self.published_conversion_factor is not None:
            object.__setattr__(
                self,
                "published_conversion_factor",
                _to_decimal(self.published_conversion_factor),
            )
        if self.maturity_date <= self.issue_date:
            raise ValueError("DeliverableBondReference requires maturity_date after issue_date.")
        if self.notional <= Decimal(0):
            raise ValueError("DeliverableBondReference notional must be positive.")

    def to_instrument(self):
        """Convert the deliverable bond reference into a bond instrument.

        The resulting instrument uses Treasury-style yield rules unless an
        explicit rule bundle is supplied.
        """
        frequency = self.frequency
        rules = self.yield_rules
        if rules is None:
            rules = YieldCalculationRules.us_treasury()
            if rules.frequency is not frequency:
                rules = replace(rules, frequency=frequency)
        elif rules.frequency is not frequency:
            rules = replace(rules, frequency=frequency)
        return (
            FixedBondBuilder.new()
            .with_issue_date(self.issue_date)
            .with_maturity_date(self.maturity_date)
            .with_coupon_rate(self.coupon_rate)
            .with_frequency(frequency)
            .with_currency(self.currency)
            .with_notional(self.notional)
            .with_instrument_id(self.instrument_id)
            .with_rules(rules)
            .build()
        )


@dataclass(frozen=True, slots=True)
class SwapReferenceData:
    """Swap reference metadata with normalized role descriptors.

    The tenor, floating index, day-count, and calendar descriptors are stored
    as normalized strings so downstream builders can map them deterministically
    onto convention objects.
    """

    instrument_id: InstrumentId
    currency: Currency = Currency.USD
    tenor: str | None = None
    floating_index: str | None = None
    fixed_frequency: Frequency | None = None
    floating_frequency: Frequency | None = None
    day_count: str | None = None
    calendar: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.tenor is not None:
            object.__setattr__(self, "tenor", self.tenor.strip().upper())
        if self.floating_index is not None:
            object.__setattr__(self, "floating_index", self.floating_index.strip().upper())
        if self.day_count is not None:
            object.__setattr__(self, "day_count", self.day_count.strip().upper())
        if self.calendar is not None:
            object.__setattr__(self, "calendar", self.calendar.strip().upper())


@dataclass(frozen=True, slots=True)
class RepoReferenceData:
    """Repo reference record with raw decimal haircut semantics.

    Haircut values are kept as raw decimals and settlement lags remain as
    integer business-day counts where supplied.
    """

    instrument_id: InstrumentId
    currency: Currency = Currency.USD
    collateral_currency: Currency | None = None
    term: str | None = None
    collateral_type: str | None = None
    haircut: Decimal | None = None
    settlement_lag_days: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.term is not None:
            object.__setattr__(self, "term", self.term.strip().upper())
        if self.collateral_type is not None:
            object.__setattr__(self, "collateral_type", self.collateral_type.strip())
        if self.haircut is not None:
            object.__setattr__(self, "haircut", _to_decimal(self.haircut))


@dataclass(frozen=True, slots=True)
class CdsReferenceData:
    """CDS reference record with raw decimal coupon and recovery fields."""

    instrument_id: InstrumentId
    reference_entity: str
    currency: Currency = Currency.USD
    tenor: str | None = None
    seniority: str | None = None
    restructuring_clause: str | None = None
    coupon: Decimal | None = None
    recovery_rate: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "reference_entity", self.reference_entity.strip())
        if self.tenor is not None:
            object.__setattr__(self, "tenor", self.tenor.strip().upper())
        if self.seniority is not None:
            object.__setattr__(self, "seniority", self.seniority.strip().upper())
        if self.restructuring_clause is not None:
            object.__setattr__(self, "restructuring_clause", self.restructuring_clause.strip().upper())
        if self.coupon is not None:
            object.__setattr__(self, "coupon", _to_decimal(self.coupon))
        if self.recovery_rate is not None:
            object.__setattr__(self, "recovery_rate", _to_decimal(self.recovery_rate))


@dataclass(frozen=True, slots=True)
class IssuerReferenceData:
    """Issuer metadata used as a lookup and normalization target.

    The issuer name is required and non-empty; optional fields are normalized
    but otherwise left as descriptive text.
    """

    issuer_name: str
    issuer_type: IssuerType = IssuerType.OTHER
    issuer_id: str | None = None
    country: str | None = None
    sector: str | None = None
    rating: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "issuer_name", self.issuer_name.strip())
        if not self.issuer_name:
            raise ValueError("issuer_name must be non-empty.")
        if self.issuer_id is not None:
            object.__setattr__(self, "issuer_id", self.issuer_id.strip())
        if self.country is not None:
            object.__setattr__(self, "country", self.country.strip().upper())
        if self.sector is not None:
            object.__setattr__(self, "sector", self.sector.strip())
        if self.rating is not None:
            object.__setattr__(self, "rating", self.rating.strip())


@dataclass(frozen=True, slots=True)
class RatingRecord:
    """Credit rating record keyed by instrument or issuer.

    Ratings are kept as simple agency buckets with optional outlook, issuer,
    instrument, and effective-date metadata.
    """

    rating: str
    agency: str | None = None
    outlook: str | None = None
    instrument_id: InstrumentId | None = None
    issuer_name: str | None = None
    effective_date: Date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rating", self.rating.strip())
        if not self.rating:
            raise ValueError("rating must be non-empty.")
        if self.agency is not None:
            object.__setattr__(self, "agency", self.agency.strip())
        if self.outlook is not None:
            object.__setattr__(self, "outlook", self.outlook.strip())
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.issuer_name is not None:
            object.__setattr__(self, "issuer_name", self.issuer_name.strip())


@runtime_checkable
class BondReferenceSource(Protocol):
    """Protocol for retrieving bond reference records by instrument id."""

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        ...


@runtime_checkable
class IssuerReferenceSource(Protocol):
    """Protocol for retrieving issuer reference records by issuer name."""

    def get_issuer_reference(self, issuer_name: str) -> IssuerReferenceData | None:
        ...


@runtime_checkable
class RatingSource(Protocol):
    """Protocol for retrieving ratings by instrument or issuer."""

    def get_rating(self, *, instrument_id: InstrumentId | str | None = None, issuer_name: str | None = None) -> RatingRecord | None:
        ...


@runtime_checkable
class EtfHoldingsSource(Protocol):
    """Protocol for retrieving ETF holdings as a normalized tuple."""

    def get_etf_holdings(self, etf_id: EtfId | str) -> tuple[EtfHolding, ...]:
        ...


@dataclass(slots=True)
class ReferenceDataProvider:
    """Composite provider that delegates to optional reference-data sources.

    Each source is optional. Missing sources return ``None`` or an empty tuple
    instead of raising, which keeps snapshot-backed workflows deterministic.
    """

    bond_source: BondReferenceSource | None = None
    issuer_source: IssuerReferenceSource | None = None
    rating_source: RatingSource | None = None
    etf_holdings_source: EtfHoldingsSource | None = None

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        """Return a bond reference from the configured bond source."""
        if self.bond_source is None:
            return None
        return self.bond_source.get_bond_reference(instrument_id)

    def get_issuer_reference(self, issuer_name: str) -> IssuerReferenceData | None:
        """Return an issuer reference from the configured issuer source."""
        if self.issuer_source is None:
            return None
        return self.issuer_source.get_issuer_reference(issuer_name)

    def get_rating(self, *, instrument_id: InstrumentId | str | None = None, issuer_name: str | None = None) -> RatingRecord | None:
        """Return a rating from the configured rating source."""
        if self.rating_source is None:
            return None
        return self.rating_source.get_rating(instrument_id=instrument_id, issuer_name=issuer_name)

    def get_etf_holdings(self, etf_id: EtfId | str) -> tuple[EtfHolding, ...]:
        """Return ETF holdings from the configured holdings source."""
        if self.etf_holdings_source is None:
            return ()
        return self.etf_holdings_source.get_etf_holdings(etf_id)


__all__ = [
    "BondFutureContractReference",
    "BondFutureReferenceData",
    "BondReferenceData",
    "BondReferenceSource",
    "BondType",
    "CdsReferenceData",
    "CallScheduleEntry",
    "DeliverableBondReference",
    "EtfHoldingsSource",
    "FloatingRateTerms",
    "FutureReferenceData",
    "IssuerReferenceData",
    "IssuerReferenceSource",
    "IssuerType",
    "RatingRecord",
    "RatingSource",
    "ReferenceDataProvider",
    "RepoReferenceData",
    "SwapReferenceData",
]
