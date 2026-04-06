"""SQLite-backed storage adapters for the trait-layer store protocols.

These stores persist JSON-coded records in SQLite and preserve deterministic
pagination, version ordering, and upsert semantics across the public store
protocols.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fuggers_py.core.types import Date
from fuggers_py.core import CurveId, InstrumentId
from fuggers_py.reference import BondReferenceData

from .storage import (
    AuditEntry,
    CurveConfig,
    CurveSnapshot,
    OverrideRecord,
    Page,
    Pagination,
    PricingConfig,
    StorageAdapter,
)

from .json_codec import JsonCodec

if TYPE_CHECKING:
    from fuggers_py.calc.config import EngineConfig


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(UTC).isoformat()


def _as_text(value: object | None) -> str | None:
    """Convert an optional value to text for SQLite parameter binding."""
    if value is None:
        return None
    return str(value)


def _ensure_parent(path: str | Path) -> None:
    """Create the parent directory for a SQLite database path if needed."""
    resolved = Path(path)
    if str(resolved) != ":memory:":
        resolved.parent.mkdir(parents=True, exist_ok=True)


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Create the SQLite schema used by the storage adapters."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS bond_references (
            instrument_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS curve_configs (
            curve_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS curve_snapshots (
            curve_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            reference_date TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (curve_id, version)
        );
        CREATE INDEX IF NOT EXISTS idx_curve_snapshots_curve_reference
            ON curve_snapshots (curve_id, reference_date, version DESC);
        CREATE TABLE IF NOT EXISTS pricing_configs (
            config_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS engine_configs (
            engine_name TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            effective_date TEXT,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_overrides_scope
            ON overrides (scope_id, field_name, effective_date, id);
        CREATE TABLE IF NOT EXISTS audit_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            actor TEXT,
            details TEXT,
            payload TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_audit_entries_entity
            ON audit_entries (entity_id, timestamp, id);
        """
    )
    connection.commit()


@dataclass(slots=True)
class _SQLiteStoreBase:
    """Common SQLite store helpers shared by the concrete adapters.

    The base class wires a shared connection, ensures the schema exists, and
    provides JSON encoding helpers for the record-oriented stores.
    """

    connection: sqlite3.Connection
    codec: JsonCodec

    def __init__(self, connection: sqlite3.Connection, codec: JsonCodec | None = None) -> None:
        self.connection = connection
        self.codec = codec or JsonCodec()
        _ensure_schema(self.connection)

    def _encode(self, value: object) -> str:
        """Encode a Python object to a JSON string for storage."""
        return self.codec.encode(value).decode("utf-8")

    def _decode(self, payload: str) -> object:
        """Decode a JSON string retrieved from SQLite."""
        return self.codec.decode(payload)


class SQLiteAuditStore(_SQLiteStoreBase):
    """SQLite-backed audit store.

    Audit entries are stored in insertion order and can be filtered by
    ``entity_id`` with cursor-as-offset pagination.
    """

    def append_audit_entry(self, entry: AuditEntry) -> AuditEntry:
        """Append an audit entry and persist its encoded payload."""
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO audit_entries (action, entity_type, entity_id, timestamp, actor, details, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.action,
                    entry.entity_type,
                    entry.entity_id,
                    entry.timestamp.isoformat(),
                    entry.actor,
                    entry.details,
                    self._encode(entry),
                ),
            )
        return entry

    def list_audit_entries(self, entity_id: str | None = None, pagination: Pagination | None = None) -> Page[AuditEntry]:
        """List audit entries with cursor-as-offset pagination."""
        pagination = pagination or Pagination()
        where = ""
        params: list[object] = []
        if entity_id is not None:
            where = "WHERE entity_id = ?"
            params.append(entity_id)
        total_row = self.connection.execute(f"SELECT COUNT(*) AS count FROM audit_entries {where}", params).fetchone()
        params.extend([pagination.limit, pagination.offset()])
        rows = self.connection.execute(
            f"""
            SELECT payload
            FROM audit_entries
            {where}
            ORDER BY timestamp ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
        items = tuple(self._decode(row["payload"]) for row in rows)
        total_items = int(total_row["count"])
        next_cursor = str(pagination.offset() + len(items)) if pagination.offset() + len(items) < total_items else None
        return Page(items=items, pagination=pagination, total_items=total_items, next_cursor=next_cursor)

    def count_audit_entries(self, entity_id: str | None = None) -> int:
        """Count audit entries, optionally filtered by entity id."""
        if entity_id is None:
            row = self.connection.execute("SELECT COUNT(*) AS count FROM audit_entries").fetchone()
        else:
            row = self.connection.execute("SELECT COUNT(*) AS count FROM audit_entries WHERE entity_id = ?", (entity_id,)).fetchone()
        return int(row["count"])


class SQLiteBondStore(_SQLiteStoreBase):
    """SQLite-backed bond reference store.

    Bond references are keyed by normalized instrument id and returned in that
    same normalized form.
    """

    def upsert_bond_reference(self, reference: BondReferenceData) -> BondReferenceData:
        """Insert or update a bond reference."""
        now = _utc_now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO bond_references (instrument_id, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (reference.instrument_id.as_str(), self._encode(reference), now, now),
            )
        return reference

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        """Return a bond reference by normalized instrument id."""
        resolved = InstrumentId.parse(instrument_id).as_str()
        row = self.connection.execute(
            "SELECT payload FROM bond_references WHERE instrument_id = ?",
            (resolved,),
        ).fetchone()
        return None if row is None else self._decode(row["payload"])

    def list_bond_references(self, pagination: Pagination | None = None) -> Page[BondReferenceData]:
        """List bond references in normalized instrument-id order."""
        pagination = pagination or Pagination()
        total_items = self.count_bond_references()
        rows = self.connection.execute(
            """
            SELECT payload
            FROM bond_references
            ORDER BY instrument_id ASC
            LIMIT ? OFFSET ?
            """,
            (pagination.limit, pagination.offset()),
        ).fetchall()
        items = tuple(self._decode(row["payload"]) for row in rows)
        next_cursor = str(pagination.offset() + len(items)) if pagination.offset() + len(items) < total_items else None
        return Page(items=items, pagination=pagination, total_items=total_items, next_cursor=next_cursor)

    def count_bond_references(self) -> int:
        """Return the total number of stored bond references."""
        row = self.connection.execute("SELECT COUNT(*) AS count FROM bond_references").fetchone()
        return int(row["count"])

    def delete_bond_reference(self, instrument_id: InstrumentId | str) -> bool:
        """Delete a bond reference by normalized instrument id."""
        resolved = InstrumentId.parse(instrument_id).as_str()
        with self.connection:
            cursor = self.connection.execute("DELETE FROM bond_references WHERE instrument_id = ?", (resolved,))
        return cursor.rowcount > 0


class SQLiteCurveStore(_SQLiteStoreBase):
    """SQLite-backed curve and curve-snapshot store.

    Curve configs are stored as single records. Snapshots are versioned per
    curve and can be queried by curve id and optional reference date.
    """

    def upsert_curve_config(self, config: CurveConfig) -> CurveConfig:
        """Insert or update a curve config."""
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO curve_configs (curve_id, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(curve_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (config.curve_id.as_str(), self._encode(config), _utc_now()),
            )
        return config

    def get_curve_config(self, curve_id: CurveId | str) -> CurveConfig | None:
        """Return a curve config by normalized curve id."""
        resolved = CurveId.parse(curve_id).as_str()
        row = self.connection.execute(
            "SELECT payload FROM curve_configs WHERE curve_id = ?",
            (resolved,),
        ).fetchone()
        return None if row is None else self._decode(row["payload"])

    def insert_curve_snapshot(self, snapshot: CurveSnapshot) -> int:
        """Insert a new curve snapshot version and return its version number."""
        curve_key = snapshot.curve_id.as_str()
        next_version_row = self.connection.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS version FROM curve_snapshots WHERE curve_id = ?",
            (curve_key,),
        ).fetchone()
        version = int(next_version_row["version"])
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO curve_snapshots (curve_id, version, reference_date, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    curve_key,
                    version,
                    snapshot.reference_date.as_naive_date().isoformat(),
                    self._encode(snapshot),
                    _utc_now(),
                ),
            )
        return version

    def get_curve_snapshot(self, curve_id: CurveId | str, reference_date: Date | None = None) -> CurveSnapshot | None:
        """Return the latest curve snapshot, optionally filtered by date."""
        resolved = CurveId.parse(curve_id).as_str()
        if reference_date is None:
            row = self.connection.execute(
                """
                SELECT payload
                FROM curve_snapshots
                WHERE curve_id = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (resolved,),
            ).fetchone()
        else:
            row = self.connection.execute(
                """
                SELECT payload
                FROM curve_snapshots
                WHERE curve_id = ? AND reference_date = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (resolved, reference_date.as_naive_date().isoformat()),
            ).fetchone()
        return None if row is None else self._decode(row["payload"])

    def list_curve_snapshots(self, curve_id: CurveId | str, pagination: Pagination | None = None) -> Page[CurveSnapshot]:
        """List curve snapshots in descending version order."""
        pagination = pagination or Pagination()
        resolved = CurveId.parse(curve_id).as_str()
        total_items = self.count_curve_snapshots(curve_id)
        rows = self.connection.execute(
            """
            SELECT payload
            FROM curve_snapshots
            WHERE curve_id = ?
            ORDER BY version DESC
            LIMIT ? OFFSET ?
            """,
            (resolved, pagination.limit, pagination.offset()),
        ).fetchall()
        items = tuple(self._decode(row["payload"]) for row in rows)
        next_cursor = str(pagination.offset() + len(items)) if pagination.offset() + len(items) < total_items else None
        return Page(items=items, pagination=pagination, total_items=total_items, next_cursor=next_cursor)

    def count_curve_snapshots(self, curve_id: CurveId | str) -> int:
        """Return the number of snapshots stored for a curve."""
        resolved = CurveId.parse(curve_id).as_str()
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM curve_snapshots WHERE curve_id = ?",
            (resolved,),
        ).fetchone()
        return int(row["count"])


class SQLiteConfigStore(_SQLiteStoreBase):
    """SQLite-backed pricing and engine configuration store."""

    def upsert_pricing_config(self, config: PricingConfig) -> PricingConfig:
        """Insert or update a pricing config."""
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO pricing_configs (config_id, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (config.config_id, self._encode(config), _utc_now()),
            )
        return config

    def get_pricing_config(self, config_id: str) -> PricingConfig | None:
        """Return a pricing config by config id."""
        row = self.connection.execute(
            "SELECT payload FROM pricing_configs WHERE config_id = ?",
            (config_id,),
        ).fetchone()
        return None if row is None else self._decode(row["payload"])

    def upsert_engine_config(self, config: EngineConfig) -> EngineConfig:
        """Insert or update an engine config."""
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO engine_configs (engine_name, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(engine_name) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (config.engine_name, self._encode(config), _utc_now()),
            )
        return config

    def get_engine_config(self, engine_name: str) -> EngineConfig | None:
        """Return an engine config by engine name."""
        row = self.connection.execute(
            "SELECT payload FROM engine_configs WHERE engine_name = ?",
            (engine_name,),
        ).fetchone()
        return None if row is None else self._decode(row["payload"])


class SQLiteOverrideStore(_SQLiteStoreBase):
    """SQLite-backed override store with optional audit logging.

    Overrides are unique per ``scope_id``/``field_name``/effective-date tuple.
    When an audit store is attached, upserts and deletes also write audit
    records.
    """

    def __init__(self, connection: sqlite3.Connection, codec: JsonCodec | None = None, *, audit_store: SQLiteAuditStore | None = None) -> None:
        super().__init__(connection, codec)
        self.audit_store = audit_store

    def save_override(self, record: OverrideRecord, *, actor: str | None = None) -> OverrideRecord:
        """Replace any existing override for the same scope, field, and date."""
        effective_date = _as_text(record.effective_date.as_naive_date().isoformat() if record.effective_date is not None else None)
        with self.connection:
            self.connection.execute(
                """
                DELETE FROM overrides
                WHERE scope_id = ? AND field_name = ?
                  AND ((effective_date IS NULL AND ? IS NULL) OR effective_date = ?)
                """,
                (record.scope_id, record.field_name, effective_date, effective_date),
            )
            self.connection.execute(
                """
                INSERT INTO overrides (scope_id, field_name, effective_date, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (record.scope_id, record.field_name, effective_date, self._encode(record), _utc_now()),
            )
        if self.audit_store is not None:
            self.audit_store.append_audit_entry(
                AuditEntry(
                    action="upsert",
                    entity_type="override",
                    entity_id=record.scope_id,
                    timestamp=datetime.now(UTC),
                    actor=actor,
                    details=f"{record.field_name}:{record.value}",
                )
            )
        return record

    def list_overrides(self, scope_id: str, pagination: Pagination | None = None) -> Page[OverrideRecord]:
        """List overrides for a scope with deterministic ordering."""
        pagination = pagination or Pagination()
        total_row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM overrides WHERE scope_id = ?",
            (scope_id,),
        ).fetchone()
        rows = self.connection.execute(
            """
            SELECT payload
            FROM overrides
            WHERE scope_id = ?
            ORDER BY field_name ASC, effective_date ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            (scope_id, pagination.limit, pagination.offset()),
        ).fetchall()
        items = tuple(self._decode(row["payload"]) for row in rows)
        total_items = int(total_row["count"])
        next_cursor = str(pagination.offset() + len(items)) if pagination.offset() + len(items) < total_items else None
        return Page(items=items, pagination=pagination, total_items=total_items, next_cursor=next_cursor)

    def delete_override(self, scope_id: str, field_name: str, effective_date: Date | None = None, *, actor: str | None = None) -> bool:
        """Delete an override and optionally emit an audit entry."""
        effective_text = _as_text(effective_date.as_naive_date().isoformat() if effective_date is not None else None)
        with self.connection:
            cursor = self.connection.execute(
                """
                DELETE FROM overrides
                WHERE scope_id = ? AND field_name = ?
                  AND ((effective_date IS NULL AND ? IS NULL) OR effective_date = ?)
                """,
                (scope_id, field_name, effective_text, effective_text),
            )
        deleted = cursor.rowcount > 0
        if deleted and self.audit_store is not None:
            self.audit_store.append_audit_entry(
                AuditEntry(
                    action="delete",
                    entity_type="override",
                    entity_id=scope_id,
                    timestamp=datetime.now(UTC),
                    actor=actor,
                    details=field_name,
                )
            )
        return deleted


class SQLiteStorageAdapter:
    """Composite SQLite-backed storage adapter.

    The adapter opens one SQLite connection and exposes the concrete bond,
    curve, config, override, and audit stores through a single facade.
    """

    def __init__(self, path: str | Path = ":memory:", *, codec: JsonCodec | None = None) -> None:
        self.path = str(path)
        _ensure_parent(self.path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        _ensure_schema(self.connection)
        self.codec = codec or JsonCodec()
        self.audit_store = SQLiteAuditStore(self.connection, self.codec)
        self.bond_store = SQLiteBondStore(self.connection, self.codec)
        self.curve_store = SQLiteCurveStore(self.connection, self.codec)
        self.config_store = SQLiteConfigStore(self.connection, self.codec)
        self.override_store = SQLiteOverrideStore(self.connection, self.codec, audit_store=self.audit_store)
        self._delegate = StorageAdapter(
            bond_store=self.bond_store,
            curve_store=self.curve_store,
            config_store=self.config_store,
            override_store=self.override_store,
            audit_store=self.audit_store,
        )

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self.connection.close()

    def __enter__(self) -> "SQLiteStorageAdapter":
        """Return the adapter for context-manager use."""
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Close the adapter when leaving a context manager."""
        self.close()

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        """Delegate bond reference lookup to the SQLite store."""
        return self._delegate.get_bond_reference(instrument_id)

    def list_bond_references(self, pagination: Pagination | None = None) -> Page[BondReferenceData]:
        """Delegate bond reference listing to the SQLite store."""
        return self._delegate.list_bond_references(pagination)

    def get_curve_config(self, curve_id: CurveId | str) -> CurveConfig | None:
        """Delegate curve config lookup to the SQLite store."""
        return self._delegate.get_curve_config(curve_id)

    def get_curve_snapshot(self, curve_id: CurveId | str, reference_date: Date | None = None) -> CurveSnapshot | None:
        """Delegate curve snapshot lookup to the SQLite store."""
        return self._delegate.get_curve_snapshot(curve_id, reference_date)

    def list_curve_snapshots(self, curve_id: CurveId | str, pagination: Pagination | None = None) -> Page[CurveSnapshot]:
        """Delegate curve snapshot listing to the SQLite store."""
        return self._delegate.list_curve_snapshots(curve_id, pagination)

    def get_pricing_config(self, config_id: str) -> PricingConfig | None:
        """Delegate pricing config lookup to the SQLite store."""
        return self._delegate.get_pricing_config(config_id)

    def get_engine_config(self, engine_name: str) -> EngineConfig | None:
        """Delegate engine config lookup to the SQLite store."""
        return self._delegate.get_engine_config(engine_name)

    def list_overrides(self, scope_id: str, pagination: Pagination | None = None) -> Page[OverrideRecord]:
        """Delegate override listing to the SQLite store."""
        return self._delegate.list_overrides(scope_id, pagination)

    def append_audit_entry(self, entry: AuditEntry) -> AuditEntry:
        """Delegate audit entry insertion to the SQLite store."""
        return self._delegate.append_audit_entry(entry)

    def list_audit_entries(self, entity_id: str | None = None, pagination: Pagination | None = None) -> Page[AuditEntry]:
        """Delegate audit entry listing to the SQLite store."""
        return self._delegate.list_audit_entries(entity_id, pagination)


__all__ = [
    "SQLiteAuditStore",
    "SQLiteBondStore",
    "SQLiteConfigStore",
    "SQLiteCurveStore",
    "SQLiteOverrideStore",
    "SQLiteStorageAdapter",
]
