from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fuggers_py.core import Date
from fuggers_py.calc import PricingSpec, QuoteSide
from fuggers_py.core import CurveId, InstrumentId, PortfolioId
from fuggers_py.market.snapshot import CurvePoint
from fuggers_py.reference import BondReferenceData, BondType, IssuerType
from fuggers_py.calc import EngineConfig
from fuggers_py.adapters import (
    AuditEntry,
    AuditStore,
    BondStore,
    ConfigStore,
    CurveConfig,
    CurveSnapshot,
    CurveStore,
    OverrideRecord,
    OverrideStore,
    Page,
    Pagination,
    PortfolioFilter,
    PortfolioStore,
    PricingConfig,
    StorageAdapter,
    StoredPortfolio,
    StoredPosition,
)


class StubBondStore:
    def __init__(self, reference: BondReferenceData) -> None:
        self.reference = reference

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        return self.reference if InstrumentId.parse(instrument_id) == self.reference.instrument_id else None

    def list_bond_references(self, pagination: Pagination | None = None) -> Page[BondReferenceData]:
        return Page((self.reference,), pagination=pagination)


class StubCurveStore:
    def __init__(self, config: CurveConfig, snapshot: CurveSnapshot) -> None:
        self.config = config
        self.snapshot = snapshot

    def get_curve_config(self, curve_id: CurveId | str) -> CurveConfig | None:
        return self.config if CurveId.parse(curve_id) == self.config.curve_id else None

    def get_curve_snapshot(self, curve_id: CurveId | str, reference_date: Date | None = None) -> CurveSnapshot | None:
        if CurveId.parse(curve_id) != self.snapshot.curve_id:
            return None
        if reference_date is not None and reference_date != self.snapshot.reference_date:
            return None
        return self.snapshot

    def list_curve_snapshots(self, curve_id: CurveId | str, pagination: Pagination | None = None) -> Page[CurveSnapshot]:
        return Page((self.snapshot,), pagination=pagination)


class StubConfigStore:
    def __init__(self, pricing_config: PricingConfig, engine_config: EngineConfig) -> None:
        self.pricing_config = pricing_config
        self.engine_config = engine_config

    def get_pricing_config(self, config_id: str) -> PricingConfig | None:
        return self.pricing_config if config_id == self.pricing_config.config_id else None

    def get_engine_config(self, engine_name: str) -> EngineConfig | None:
        return self.engine_config if engine_name == self.engine_config.engine_name else None


class StubOverrideStore:
    def __init__(self, record: OverrideRecord) -> None:
        self.record = record

    def list_overrides(self, scope_id: str, pagination: Pagination | None = None) -> Page[OverrideRecord]:
        items = (self.record,) if scope_id == self.record.scope_id else ()
        return Page(items, pagination=pagination)


class StubAuditStore:
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    def append_audit_entry(self, entry: AuditEntry) -> AuditEntry:
        self.entries.append(entry)
        return entry

    def list_audit_entries(self, entity_id: str | None = None, pagination: Pagination | None = None) -> Page[AuditEntry]:
        items = tuple(entry for entry in self.entries if entity_id is None or entry.entity_id == entity_id)
        return Page(items, pagination=pagination)


class StubPortfolioStore:
    def __init__(self, portfolio: StoredPortfolio) -> None:
        self.portfolio = portfolio

    def get_portfolio(self, portfolio_id: PortfolioId | str, as_of: Date | None = None) -> StoredPortfolio | None:
        resolved = PortfolioId.parse(portfolio_id)
        if resolved != self.portfolio.portfolio_id:
            return None
        if as_of is not None and as_of != self.portfolio.as_of:
            return None
        return self.portfolio

    def list_portfolios(self, portfolio_filter: PortfolioFilter | None = None, pagination: Pagination | None = None) -> Page[StoredPortfolio]:
        items = (self.portfolio,)
        if portfolio_filter is not None and not portfolio_filter.matches(self.portfolio):
            items = ()
        return Page(items, pagination=pagination)


def test_pagination_and_page_helpers() -> None:
    page = Page.from_sequence([1, 2, 3], Pagination(limit=2))

    assert page.items == (1, 2)
    assert page.total_items == 3
    assert page.next_cursor == "2"
    assert page.has_next is True


def test_storage_adapter_delegates_to_component_stores() -> None:
    bond_reference = BondReferenceData(
        instrument_id=InstrumentId("STORE-1"),
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 1),
        maturity_date=Date.from_ymd(2030, 1, 1),
        coupon_rate=Decimal("0.04"),
    )
    curve_config = CurveConfig(curve_id=CurveId("usd.discount"), curve_kind="zero", interpolation="linear")
    curve_snapshot = CurveSnapshot(
        curve_id=CurveId("usd.discount"),
        reference_date=Date.from_ymd(2026, 3, 13),
        points=(CurvePoint(Decimal("1.0"), Decimal("0.04")),),
    )
    pricing_config = PricingConfig(config_id="base", pricing_spec=PricingSpec(quote_side=QuoteSide.MID))
    engine_config = EngineConfig(engine_name="engine")
    override = OverrideRecord(scope_id="STORE-1", field_name="spread", value="0.0010", numeric_value=Decimal("0.0010"))
    stored_portfolio = StoredPortfolio(
        portfolio_id=PortfolioId("fixture-portfolio"),
        positions=(StoredPosition("STORE-1", quantity=Decimal("100")),),
        as_of=Date.from_ymd(2026, 3, 13),
    )
    audit = AuditEntry(
        action="upsert",
        entity_type="curve_snapshot",
        entity_id="usd.discount",
        timestamp=datetime(2026, 3, 13, 10, 0),
        actor="test",
    )
    audit_store = StubAuditStore()

    adapter = StorageAdapter(
        bond_store=StubBondStore(bond_reference),
        curve_store=StubCurveStore(curve_config, curve_snapshot),
        config_store=StubConfigStore(pricing_config, engine_config),
        override_store=StubOverrideStore(override),
        audit_store=audit_store,
        portfolio_store=StubPortfolioStore(stored_portfolio),
    )

    assert isinstance(adapter, BondStore)
    assert isinstance(adapter, CurveStore)
    assert isinstance(adapter, ConfigStore)
    assert isinstance(adapter, OverrideStore)
    assert isinstance(adapter, AuditStore)
    assert isinstance(adapter, PortfolioStore)
    assert adapter.get_bond_reference("STORE-1") == bond_reference
    assert adapter.get_curve_config("usd.discount") == curve_config
    assert adapter.get_curve_snapshot("usd.discount") == curve_snapshot
    assert adapter.get_pricing_config("base") == pricing_config
    assert adapter.get_engine_config("engine") == engine_config
    assert adapter.list_overrides("STORE-1").items == (override,)
    assert adapter.append_audit_entry(audit) == audit
    assert adapter.list_audit_entries("usd.discount").items == (audit,)
    assert adapter.get_portfolio("fixture-portfolio") == stored_portfolio
    assert adapter.list_portfolios(PortfolioFilter(portfolio_ids=(PortfolioId("fixture-portfolio"),))).items == (stored_portfolio,)
