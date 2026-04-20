from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._storage import SQLiteStorageAdapter
from fuggers_py._calc import PricingSpec, QuoteSide
from fuggers_py.bonds.types import BondType, IssuerType
from fuggers_py._core import CurveId, InstrumentId
from fuggers_py._market.snapshot import CurvePoint
from fuggers_py._reference import BondReferenceData
from fuggers_py._calc import EngineConfig, NodeConfig, UpdateFrequency
from fuggers_py._storage import (
    AuditEntry,
    CurveConfig,
    CurveSnapshot,
    OverrideRecord,
    Pagination,
    PricingConfig,
)


def _bond_reference() -> BondReferenceData:
    return BondReferenceData(
        instrument_id=InstrumentId("SQL-1"),
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.0450"),
        frequency=Frequency.SEMI_ANNUAL,
        issuer_name="SQLite Corp",
    )


def test_sqlite_bond_store_supports_insert_get_list_count_delete() -> None:
    with SQLiteStorageAdapter(":memory:") as storage:
        reference = _bond_reference()

        storage.bond_store.upsert_bond_reference(reference)

        assert storage.get_bond_reference("SQL-1") == reference
        assert storage.bond_store.count_bond_references() == 1
        assert storage.list_bond_references(Pagination(limit=1)).items == (reference,)
        assert storage.bond_store.delete_bond_reference("SQL-1") is True
        assert storage.bond_store.count_bond_references() == 0


def test_sqlite_curve_config_override_and_audit_flows_work_in_memory() -> None:
    with SQLiteStorageAdapter(":memory:") as storage:
        curve_config = CurveConfig(curve_id=CurveId("usd.discount"), curve_kind="zero", interpolation="linear", source="fixture")
        curve_snapshot = CurveSnapshot(
            curve_id=CurveId("usd.discount"),
            reference_date=Date.from_ymd(2026, 3, 13),
            points=(CurvePoint(Decimal("1.0"), Decimal("0.0425")), CurvePoint(Decimal("5.0"), Decimal("0.0390"))),
            source="fixture",
        )
        pricing_config = PricingConfig(config_id="base", pricing_spec=PricingSpec(quote_side=QuoteSide.MID), source="fixture")
        engine_config = EngineConfig(
            engine_name="pricing-engine",
            update_frequency=UpdateFrequency.INTRADAY,
            nodes=(NodeConfig(node_id="node-1", service_name="pricing"),),
        )
        override = OverrideRecord(
            scope_id="SQL-1",
            field_name="spread",
            value="0.0010",
            numeric_value=Decimal("0.0010"),
            side=QuoteSide.MID,
            effective_date=Date.from_ymd(2026, 3, 13),
            source="manual",
        )

        version_1 = storage.curve_store.insert_curve_snapshot(curve_snapshot)
        version_2 = storage.curve_store.insert_curve_snapshot(curve_snapshot)
        storage.curve_store.upsert_curve_config(curve_config)
        storage.config_store.upsert_pricing_config(pricing_config)
        storage.config_store.upsert_engine_config(engine_config)
        storage.override_store.save_override(override, actor="tester")
        storage.append_audit_entry(
            AuditEntry(
                action="snapshot",
                entity_type="curve",
                entity_id="usd.discount",
                timestamp=datetime(2026, 3, 13, 10, 0),
                actor="tester",
            )
        )

        assert (version_1, version_2) == (1, 2)
        assert storage.get_curve_config("usd.discount") == curve_config
        assert storage.get_curve_snapshot("usd.discount") == curve_snapshot
        assert storage.curve_store.count_curve_snapshots("usd.discount") == 2
        assert storage.list_curve_snapshots("usd.discount", Pagination(limit=1)).items == (curve_snapshot,)
        assert storage.get_pricing_config("base") == pricing_config
        assert storage.get_engine_config("pricing-engine") == engine_config
        assert storage.list_overrides("SQL-1").items == (override,)
        assert storage.audit_store.count_audit_entries() == 2
        assert storage.list_audit_entries("usd.discount").items[-1].entity_id == "usd.discount"


def test_sqlite_storage_persists_on_temp_file_and_pagination_is_deterministic(tmp_path) -> None:
    db_path = tmp_path / "storage.sqlite"

    with SQLiteStorageAdapter(db_path) as storage:
        storage.bond_store.upsert_bond_reference(_bond_reference())
        storage.bond_store.upsert_bond_reference(
            BondReferenceData(
                instrument_id=InstrumentId("SQL-2"),
                bond_type=BondType.ZERO_COUPON,
                issuer_type=IssuerType.SOVEREIGN,
                issue_date=Date.from_ymd(2025, 1, 1),
                maturity_date=Date.from_ymd(2027, 1, 1),
                currency=Currency.USD,
            )
        )

    with SQLiteStorageAdapter(db_path) as storage:
        first_page = storage.list_bond_references(Pagination(limit=1))
        second_page = storage.list_bond_references(Pagination(limit=1, cursor=first_page.next_cursor))

        assert first_page.total_items == 2
        assert first_page.items[0].instrument_id == InstrumentId("SQL-1")
        assert second_page.items[0].instrument_id == InstrumentId("SQL-2")
        assert second_page.has_next is False
