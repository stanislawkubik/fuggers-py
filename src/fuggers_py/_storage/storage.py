"""Storage-oriented protocols and lightweight records.

Pagination uses cursor-as-offset semantics. Stored records normalize
identifiers, keep deterministic ordering where ordering matters, and preserve
quantity and weight values as raw decimals with explicit non-negativity checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar, runtime_checkable

from fuggers_py._core.types import Currency, Date
from fuggers_py._core.ids import CurveId, InstrumentId, PortfolioId
from fuggers_py._runtime.pricing_specs import PricingSpec
from fuggers_py._runtime.snapshot import CurvePoint
from fuggers_py._runtime.state import QuoteSide
from fuggers_py.bonds.reference_data import BondReferenceData

if TYPE_CHECKING:
    from fuggers_py._runtime.config import EngineConfig


T = TypeVar("T")


def _to_decimal(value: object | None) -> Decimal | None:
    """Coerce a nullable storage scalar to ``Decimal``."""
    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class Pagination:
    """Cursor-based pagination window.

    Parameters
    ----------
    limit:
        Maximum number of records to return in one page.
    cursor:
        Zero-based offset encoded as text. ``None`` starts from the beginning.
    """

    limit: int = 100
    cursor: str | None = None

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("Pagination.limit must be positive.")

    def offset(self) -> int:
        """Interpret the cursor as a zero-based offset."""
        if self.cursor is None:
            return 0
        return int(self.cursor)


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """Paginated result page.

    Parameters
    ----------
    items:
        Records in the current page, ordered according to the backing store.
    pagination:
        Pagination request that produced the page.
    total_items:
        Total number of matching records across all pages.
    next_cursor:
        Cursor for the next page, or ``None`` when no further page exists.
    """

    items: tuple[T, ...]
    pagination: Pagination | None = None
    total_items: int | None = None
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        total = len(self.items) if self.total_items is None else self.total_items
        object.__setattr__(self, "total_items", total)

    @classmethod
    def from_sequence(cls, items: list[T] | tuple[T, ...], pagination: Pagination) -> "Page[T]":
        """Slice a sequence using cursor-as-offset pagination semantics."""
        offset = pagination.offset()
        total = len(items)
        window = tuple(items[offset : offset + pagination.limit])
        next_cursor = str(offset + len(window)) if offset + len(window) < total else None
        return cls(items=window, pagination=pagination, total_items=total, next_cursor=next_cursor)

    @property
    def has_next(self) -> bool:
        """Return whether another page is available."""
        return self.next_cursor is not None


@dataclass(frozen=True, slots=True)
class CurveConfig:
    """Configuration record for a stored curve.

    Parameters
    ----------
    curve_id:
        Normalized curve identifier.
    curve_kind:
        Logical curve family such as ``zero`` or ``forward``.
    interpolation:
        Interpolation label used by the curve consumer.
    source:
        Optional provenance label for the stored record.
    description:
        Optional human-readable description.
    """

    curve_id: CurveId
    curve_kind: str = "zero"
    interpolation: str = "linear"
    source: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "curve_id", CurveId.parse(self.curve_id))
        object.__setattr__(self, "curve_kind", self.curve_kind.strip().lower())
        object.__setattr__(self, "interpolation", self.interpolation.strip().lower())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        if self.description is not None:
            object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class CurveSnapshot:
    """Stored curve snapshot with deterministic point ordering.

    Parameters
    ----------
    curve_id:
        Normalized curve identifier.
    reference_date:
        Curve reference date used to interpret the snapshot.
    points:
        Curve points stored in deterministic tenor/value order.
    as_of:
        Optional as-of date for the snapshot record.
    timestamp:
        Optional capture timestamp.
    source:
        Optional provenance label for the stored snapshot.
    """

    curve_id: CurveId
    reference_date: Date
    points: tuple[CurvePoint, ...]
    as_of: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        ordered_points = tuple(sorted(self.points, key=lambda point: (point.tenor, point.value)))
        object.__setattr__(self, "curve_id", CurveId.parse(self.curve_id))
        object.__setattr__(self, "points", ordered_points)
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())


@dataclass(frozen=True, slots=True)
class PricingConfig:
    """Stored pricing configuration keyed by config id.

    Parameters
    ----------
    config_id:
        Stable configuration identifier.
    pricing_spec:
        Pricing specification attached to the stored record.
    source:
        Optional provenance label for the stored record.
    as_of:
        Optional as-of date for the configuration.
    description:
        Optional human-readable description.
    """

    config_id: str
    pricing_spec: PricingSpec = field(default_factory=PricingSpec)
    source: str | None = None
    as_of: Date | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "config_id", self.config_id.strip())
        if not self.config_id:
            raise ValueError("config_id must be non-empty.")
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        if self.description is not None:
            object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class OverrideRecord:
    """Override record with string and optional numeric payload values.

    Parameters
    ----------
    scope_id:
        Override scope, such as a desk, strategy, or portfolio id.
    field_name:
        Name of the overridden field.
    value:
        Stored override value as text.
    side:
        Optional quote side when the override applies to a market quote.
    effective_date:
        Optional date from which the override applies.
    numeric_value:
        Optional parsed numeric form of ``value`` stored as a raw decimal.
    source:
        Optional provenance label.
    reason:
        Optional free-text explanation.
    """

    scope_id: str
    field_name: str
    value: str
    side: QuoteSide | None = None
    effective_date: Date | None = None
    numeric_value: Decimal | None = None
    source: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope_id", self.scope_id.strip())
        object.__setattr__(self, "field_name", self.field_name.strip())
        object.__setattr__(self, "value", self.value.strip())
        if not self.scope_id or not self.field_name:
            raise ValueError("scope_id and field_name must be non-empty.")
        numeric_value = _to_decimal(self.numeric_value)
        if numeric_value is not None:
            object.__setattr__(self, "numeric_value", numeric_value)
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        if self.reason is not None:
            object.__setattr__(self, "reason", self.reason.strip())


@dataclass(frozen=True, slots=True)
class StoredPosition:
    """Stored portfolio position with quantity or weight semantics.

    At least one of ``quantity`` or ``weight`` must be supplied. When present,
    both are interpreted as raw decimals and must be non-negative.

    Parameters
    ----------
    instrument_id:
        Normalized instrument identifier.
    quantity:
        Optional position quantity in instrument units.
    weight:
        Optional portfolio weight as a raw decimal fraction.
    label:
        Optional descriptive label for the position.
    metadata:
        Free-form string metadata preserved with deterministic key ordering.
    """

    instrument_id: InstrumentId
    quantity: Decimal | None = None
    weight: Decimal | None = None
    label: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        quantity = _to_decimal(self.quantity)
        weight = _to_decimal(self.weight)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "weight", weight)
        if quantity is None and weight is None:
            raise ValueError("StoredPosition requires either quantity or weight.")
        if quantity is not None and quantity < 0:
            raise ValueError("StoredPosition.quantity must be non-negative.")
        if weight is not None and weight < 0:
            raise ValueError("StoredPosition.weight must be non-negative.")
        if self.label is not None:
            object.__setattr__(self, "label", self.label.strip())
        object.__setattr__(
            self,
            "metadata",
            {str(key).strip(): str(value).strip() for key, value in sorted(self.metadata.items())},
        )


@dataclass(frozen=True, slots=True)
class StoredPortfolio:
    """Stored portfolio with deterministic position ordering.

    Parameters
    ----------
    portfolio_id:
        Normalized portfolio identifier.
    positions:
        Stored positions in the portfolio.
    as_of:
        Optional snapshot date for the portfolio.
    currency:
        Optional portfolio currency.
    name:
        Optional human-readable portfolio name.
    source:
        Optional provenance label for the stored record.
    """

    portfolio_id: PortfolioId
    positions: tuple[StoredPosition, ...]
    as_of: Date | None = None
    currency: Currency | None = None
    name: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "portfolio_id", PortfolioId.parse(self.portfolio_id))
        ordered_positions = tuple(
            sorted(
                self.positions,
                key=lambda position: (
                    position.instrument_id.as_str(),
                    "" if position.label is None else position.label,
                ),
            )
        )
        object.__setattr__(self, "positions", ordered_positions)
        if self.currency is not None and not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        if self.name is not None:
            object.__setattr__(self, "name", self.name.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())

    @property
    def position_count(self) -> int:
        """Return the number of stored positions."""
        return len(self.positions)

    def contains_instrument(self, instrument_id: InstrumentId | str) -> bool:
        """Return whether the portfolio contains the requested instrument."""
        resolved = InstrumentId.parse(instrument_id)
        return any(position.instrument_id == resolved for position in self.positions)


@dataclass(frozen=True, slots=True)
class PortfolioFilter:
    """Filter for stored portfolios by metadata and membership.

    Parameters
    ----------
    portfolio_ids:
        Optional portfolio identifiers to match.
    as_of:
        Optional as-of date to match.
    currency:
        Optional currency to match.
    source:
        Optional provenance label to match.
    instrument_id:
        Optional instrument membership filter.
    name_contains:
        Optional case-insensitive substring filter for the portfolio name.
    """

    portfolio_ids: tuple[PortfolioId, ...] = ()
    as_of: Date | None = None
    currency: Currency | None = None
    source: str | None = None
    instrument_id: InstrumentId | None = None
    name_contains: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "portfolio_ids", tuple(PortfolioId.parse(value) for value in self.portfolio_ids))
        if self.currency is not None and not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.name_contains is not None:
            object.__setattr__(self, "name_contains", self.name_contains.strip().lower())

    def matches(self, portfolio: StoredPortfolio) -> bool:
        """Return whether a stored portfolio satisfies the filter."""
        if self.portfolio_ids and portfolio.portfolio_id not in self.portfolio_ids:
            return False
        if self.as_of is not None and portfolio.as_of != self.as_of:
            return False
        if self.currency is not None and portfolio.currency != self.currency:
            return False
        if self.source is not None and portfolio.source != self.source:
            return False
        if self.instrument_id is not None and not portfolio.contains_instrument(self.instrument_id):
            return False
        if self.name_contains is not None:
            name = "" if portfolio.name is None else portfolio.name.lower()
            if self.name_contains not in name:
                return False
        return True


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Audit log entry stored alongside other persistence records.

    Parameters
    ----------
    action:
        Action that occurred, such as ``upsert`` or ``delete``.
    entity_type:
        Type of entity that was changed.
    entity_id:
        Identifier of the changed entity.
    timestamp:
        Timestamp for the event.
    actor:
        Optional actor responsible for the change.
    details:
        Optional free-text detail payload.
    """

    action: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    actor: str | None = None
    details: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", self.action.strip())
        object.__setattr__(self, "entity_type", self.entity_type.strip())
        object.__setattr__(self, "entity_id", self.entity_id.strip())
        if not self.action or not self.entity_type or not self.entity_id:
            raise ValueError("action, entity_type, and entity_id must be non-empty.")
        if self.actor is not None:
            object.__setattr__(self, "actor", self.actor.strip())
        if self.details is not None:
            object.__setattr__(self, "details", self.details.strip())


@runtime_checkable
class BondStore(Protocol):
    """Protocol for bond-reference persistence.

    Implementations return normalized bond reference data and support
    cursor-based listing when multiple records are available.
    """

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        ...

    def list_bond_references(self, pagination: Pagination | None = None) -> Page[BondReferenceData]:
        ...


@runtime_checkable
class CurveStore(Protocol):
    """Protocol for curve configuration and snapshot persistence.

    Curve configs identify how a curve should be interpreted, while snapshots
    store the dated point set used by downstream consumers.
    """

    def get_curve_config(self, curve_id: CurveId | str) -> CurveConfig | None:
        ...

    def get_curve_snapshot(self, curve_id: CurveId | str, reference_date: Date | None = None) -> CurveSnapshot | None:
        ...

    def list_curve_snapshots(self, curve_id: CurveId | str, pagination: Pagination | None = None) -> Page[CurveSnapshot]:
        ...


@runtime_checkable
class ConfigStore(Protocol):
    """Protocol for pricing and engine configuration persistence."""

    def get_pricing_config(self, config_id: str) -> PricingConfig | None:
        ...

    def get_engine_config(self, engine_name: str) -> EngineConfig | None:
        ...


@runtime_checkable
class OverrideStore(Protocol):
    """Protocol for override persistence."""

    def list_overrides(self, scope_id: str, pagination: Pagination | None = None) -> Page[OverrideRecord]:
        ...


@runtime_checkable
class AuditStore(Protocol):
    """Protocol for audit-log persistence."""

    def append_audit_entry(self, entry: AuditEntry) -> AuditEntry:
        ...

    def list_audit_entries(self, entity_id: str | None = None, pagination: Pagination | None = None) -> Page[AuditEntry]:
        ...


@runtime_checkable
class PortfolioStore(Protocol):
    """Protocol for stored portfolio retrieval and listing."""

    def get_portfolio(self, portfolio_id: PortfolioId | str, as_of: Date | None = None) -> StoredPortfolio | None:
        ...

    def list_portfolios(
        self,
        portfolio_filter: PortfolioFilter | None = None,
        pagination: Pagination | None = None,
    ) -> Page[StoredPortfolio]:
        ...


@dataclass(slots=True)
class StorageAdapter:
    """Composite storage adapter over optional store implementations.

    Each method delegates to the configured store when present and otherwise
    returns the empty or missing value that best matches the store contract.
    """

    bond_store: BondStore | None = None
    curve_store: CurveStore | None = None
    config_store: ConfigStore | None = None
    override_store: OverrideStore | None = None
    audit_store: AuditStore | None = None
    portfolio_store: PortfolioStore | None = None

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        """Return a bond reference from the configured store, or ``None``."""
        if self.bond_store is None:
            return None
        return self.bond_store.get_bond_reference(instrument_id)

    def list_bond_references(self, pagination: Pagination | None = None) -> Page[BondReferenceData]:
        """List bond references or return an empty page when no store exists."""
        if self.bond_store is None:
            return Page(())
        return self.bond_store.list_bond_references(pagination)

    def get_curve_config(self, curve_id: CurveId | str) -> CurveConfig | None:
        """Return a curve config from the configured store, or ``None``."""
        if self.curve_store is None:
            return None
        return self.curve_store.get_curve_config(curve_id)

    def get_curve_snapshot(self, curve_id: CurveId | str, reference_date: Date | None = None) -> CurveSnapshot | None:
        """Return a curve snapshot from the configured store, or ``None``."""
        if self.curve_store is None:
            return None
        return self.curve_store.get_curve_snapshot(curve_id, reference_date)

    def list_curve_snapshots(self, curve_id: CurveId | str, pagination: Pagination | None = None) -> Page[CurveSnapshot]:
        """List curve snapshots or return an empty page when no store exists."""
        if self.curve_store is None:
            return Page(())
        return self.curve_store.list_curve_snapshots(curve_id, pagination)

    def get_pricing_config(self, config_id: str) -> PricingConfig | None:
        """Return a pricing config from the configured store, or ``None``."""
        if self.config_store is None:
            return None
        return self.config_store.get_pricing_config(config_id)

    def get_engine_config(self, engine_name: str) -> EngineConfig | None:
        """Return an engine config from the configured store, or ``None``."""
        if self.config_store is None:
            return None
        return self.config_store.get_engine_config(engine_name)

    def list_overrides(self, scope_id: str, pagination: Pagination | None = None) -> Page[OverrideRecord]:
        """List overrides or return an empty page when no store exists."""
        if self.override_store is None:
            return Page(())
        return self.override_store.list_overrides(scope_id, pagination)

    def append_audit_entry(self, entry: AuditEntry) -> AuditEntry:
        """Append an audit entry or return the input entry when no store exists."""
        if self.audit_store is None:
            return entry
        return self.audit_store.append_audit_entry(entry)

    def list_audit_entries(self, entity_id: str | None = None, pagination: Pagination | None = None) -> Page[AuditEntry]:
        """List audit entries or return an empty page when no store exists."""
        if self.audit_store is None:
            return Page(())
        return self.audit_store.list_audit_entries(entity_id, pagination)

    def get_portfolio(self, portfolio_id: PortfolioId | str, as_of: Date | None = None) -> StoredPortfolio | None:
        """Return a stored portfolio from the configured store, or ``None``."""
        if self.portfolio_store is None:
            return None
        return self.portfolio_store.get_portfolio(portfolio_id, as_of)

    def list_portfolios(
        self,
        portfolio_filter: PortfolioFilter | None = None,
        pagination: Pagination | None = None,
    ) -> Page[StoredPortfolio]:
        """List portfolios or return an empty page when no store exists."""
        if self.portfolio_store is None:
            return Page(())
        return self.portfolio_store.list_portfolios(portfolio_filter, pagination)


__all__ = [
    "AuditEntry",
    "AuditStore",
    "BondStore",
    "ConfigStore",
    "CurveConfig",
    "CurveSnapshot",
    "CurveStore",
    "OverrideRecord",
    "OverrideStore",
    "Page",
    "Pagination",
    "PortfolioFilter",
    "PortfolioStore",
    "PricingConfig",
    "QuoteSide",
    "StorageAdapter",
    "StoredPortfolio",
    "StoredPosition",
]
