from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py.market.indices import BondIndex, IndexConventions, IndexFixingStore, OvernightCompounding
from fuggers_py.products.bonds.instruments import CallableBondBuilder, FixedBond, FloatingRateNoteBuilder
from fuggers_py.reference.bonds.types import RateIndex, YieldCalculationRules
from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.calc import CurveBuilder, PricingRouter
from fuggers_py.portfolio import PortfolioPosition
from fuggers_py.calc import AnalyticsCurves, PricingSpec, QuoteSide
from fuggers_py.core import CurveId, InstrumentId
from fuggers_py.market.quotes import RawQuote
from fuggers_py.market.snapshot import CurvePoint, EtfHolding, IndexFixing, MarketDataSnapshot
from fuggers_py.market.sources import InMemoryFixingSource
from fuggers_py.reference import (
    BondReferenceData,
    BondType,
    CallScheduleEntry,
    IssuerType,
    FloatingRateTerms,
)


SETTLEMENT = Date.from_ymd(2026, 1, 15)
FIXED_ID = InstrumentId("SCENARIO-A-FIXED")
CALLABLE_ID = InstrumentId("SCENARIO-B-CALLABLE")
FRN_ID = InstrumentId("SCENARIO-C-FRN")
ETF_ID = "SCENARIO-D-ETF"
PORTFOLIO_ID = "SCENARIO-E-PORTFOLIO"

DISCOUNT_ID = CurveId("usd.discount")
GOVERNMENT_ID = CurveId("usd.government")
BENCHMARK_ID = CurveId("usd.benchmark")
FORWARD_ID = CurveId("usd.forward")


def scenario_a_curve_points() -> list[CurvePoint]:
    return [
        CurvePoint(Decimal("0.25"), Decimal("0.0450")),
        CurvePoint(Decimal("0.50"), Decimal("0.0445")),
        CurvePoint(Decimal("1.00"), Decimal("0.0435")),
        CurvePoint(Decimal("2.00"), Decimal("0.0415")),
        CurvePoint(Decimal("5.00"), Decimal("0.0395")),
        CurvePoint(Decimal("10.00"), Decimal("0.0400")),
    ]


def scenario_a_government_points() -> list[CurvePoint]:
    return [
        CurvePoint(Decimal("0.25"), Decimal("0.0420")),
        CurvePoint(Decimal("0.50"), Decimal("0.0410")),
        CurvePoint(Decimal("1.00"), Decimal("0.0400")),
        CurvePoint(Decimal("2.00"), Decimal("0.0385")),
        CurvePoint(Decimal("5.00"), Decimal("0.0370")),
        CurvePoint(Decimal("10.00"), Decimal("0.0380")),
    ]


def scenario_a_benchmark_points() -> list[CurvePoint]:
    return [
        CurvePoint(Decimal("0.25"), Decimal("0.0435")),
        CurvePoint(Decimal("0.50"), Decimal("0.0428")),
        CurvePoint(Decimal("1.00"), Decimal("0.0418")),
        CurvePoint(Decimal("2.00"), Decimal("0.0402")),
        CurvePoint(Decimal("5.00"), Decimal("0.0388")),
        CurvePoint(Decimal("10.00"), Decimal("0.0392")),
    ]


def scenario_c_curve_points() -> list[CurvePoint]:
    return [
        CurvePoint(Decimal("0.25"), Decimal("0.0430")),
        CurvePoint(Decimal("0.50"), Decimal("0.0420")),
        CurvePoint(Decimal("1.00"), Decimal("0.0405")),
        CurvePoint(Decimal("2.00"), Decimal("0.0390")),
        CurvePoint(Decimal("3.00"), Decimal("0.0385")),
    ]


def curve_builder_with_scenarios() -> CurveBuilder:
    builder = CurveBuilder()
    builder.add_zero_curve(DISCOUNT_ID, scenario_a_curve_points(), SETTLEMENT)
    builder.add_zero_curve(GOVERNMENT_ID, scenario_a_government_points(), SETTLEMENT)
    builder.add_zero_curve(BENCHMARK_ID, scenario_a_benchmark_points(), SETTLEMENT)
    builder.add_zero_curve(CurveId("frn.discount"), scenario_c_curve_points(), SETTLEMENT)
    builder.add_forward_curve(FORWARD_ID, scenario_c_curve_points(), SETTLEMENT)
    return builder


def scenario_a_instrument() -> FixedBond:
    rules = replace(YieldCalculationRules.us_corporate(), frequency=Frequency.SEMI_ANNUAL)
    return FixedBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        coupon_rate=Decimal("0.0450"),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
        notional=Decimal("100"),
        rules=rules,
    )


def scenario_b_instrument():
    rules = replace(YieldCalculationRules.us_corporate(), frequency=Frequency.SEMI_ANNUAL)
    base = FixedBond.new(
        issue_date=Date.from_ymd(2023, 1, 15),
        maturity_date=Date.from_ymd(2033, 1, 15),
        coupon_rate=Decimal("0.0500"),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
        notional=Decimal("100"),
        rules=rules,
    )
    builder = CallableBondBuilder.new().with_base_bond(base)
    for year in range(2028, 2033):
        builder = builder.add_call(call_date=Date.from_ymd(year, 1, 15), call_price=Decimal("100.00"))
    return builder.build()


def scenario_c_fixing_source() -> InMemoryFixingSource:
    fixings = [
        IndexFixing("SOFR", Date.from_ymd(2025, 12, 29), Decimal("0.0408")),
        IndexFixing("SOFR", Date.from_ymd(2025, 12, 30), Decimal("0.0409")),
        IndexFixing("SOFR", Date.from_ymd(2025, 12, 31), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 2), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 5), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 6), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 7), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 8), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 9), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 12), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 13), Decimal("0.0410")),
        IndexFixing("SOFR", Date.from_ymd(2026, 1, 14), Decimal("0.0410")),
    ]
    return InMemoryFixingSource(fixings)


def scenario_c_instrument():
    store = scenario_c_fixing_source().to_fixing_store()
    index = BondIndex(
        name="SOFR",
        rate_index=RateIndex.SOFR,
        currency=Currency.USD,
        fixing_store=store,
        conventions=IndexConventions(overnight_compounding=OvernightCompounding.COMPOUNDED),
    )
    rules = replace(YieldCalculationRules.us_treasury(), frequency=Frequency.QUARTERLY)
    return (
        FloatingRateNoteBuilder.new()
        .with_issue_date(Date.from_ymd(2025, 1, 15))
        .with_maturity_date(Date.from_ymd(2028, 1, 15))
        .with_index(RateIndex.SOFR)
        .with_index_definition(index)
        .with_quoted_spread(Decimal("0.0125"))
        .with_frequency(Frequency.QUARTERLY)
        .with_currency(Currency.USD)
        .with_notional(Decimal("100"))
        .with_rules(rules)
        .with_current_reference_rate(Decimal("0.0410"))
        .build()
    )


def fixed_curves() -> AnalyticsCurves:
    builder = curve_builder_with_scenarios()
    return AnalyticsCurves(
        discount_curve=builder.get(DISCOUNT_ID),
        government_curve=builder.get(GOVERNMENT_ID),
        benchmark_curve=builder.get(BENCHMARK_ID),
    )


def frn_curves() -> AnalyticsCurves:
    builder = curve_builder_with_scenarios()
    return AnalyticsCurves(
        discount_curve=builder.get("frn.discount"),
        forward_curve=builder.get(FORWARD_ID),
    )


def scenario_market_data() -> MarketDataSnapshot:
    return MarketDataSnapshot(
        as_of=SETTLEMENT,
        quotes=(
            RawQuote(FIXED_ID, Decimal("101.25"), as_of=SETTLEMENT, currency=Currency.USD),
            RawQuote(CALLABLE_ID, Decimal("102.50"), as_of=SETTLEMENT, currency=Currency.USD),
            RawQuote(FRN_ID, Decimal("100.15"), as_of=SETTLEMENT, currency=Currency.USD),
        ),
        fixings=tuple(scenario_c_fixing_source().fixings.values()),
    )


def scenario_reference_data() -> dict[InstrumentId, BondReferenceData]:
    return {
        FIXED_ID: BondReferenceData(
            instrument_id=FIXED_ID,
            bond_type=BondType.FIXED_RATE,
            issuer_type=IssuerType.CORPORATE,
            issue_date=Date.from_ymd(2024, 1, 15),
            maturity_date=Date.from_ymd(2031, 1, 15),
            currency=Currency.USD,
            coupon_rate=Decimal("0.0450"),
            frequency=Frequency.SEMI_ANNUAL,
            sector="CORPORATE",
            rating="A",
        ),
        CALLABLE_ID: BondReferenceData(
            instrument_id=CALLABLE_ID,
            bond_type=BondType.CALLABLE,
            issuer_type=IssuerType.CORPORATE,
            issue_date=Date.from_ymd(2023, 1, 15),
            maturity_date=Date.from_ymd(2033, 1, 15),
            currency=Currency.USD,
            coupon_rate=Decimal("0.0500"),
            frequency=Frequency.SEMI_ANNUAL,
            call_schedule=tuple(
                CallScheduleEntry(Date.from_ymd(year, 1, 15), Decimal("100.00")) for year in range(2028, 2033)
            ),
            sector="FINANCIALS",
            rating="BBB",
        ),
        FRN_ID: BondReferenceData(
            instrument_id=FRN_ID,
            bond_type=BondType.FLOATING_RATE,
            issuer_type=IssuerType.CORPORATE,
            issue_date=Date.from_ymd(2025, 1, 15),
            maturity_date=Date.from_ymd(2028, 1, 15),
            currency=Currency.USD,
            floating_rate_terms=FloatingRateTerms(
                index_name="SOFR",
                spread=Decimal("0.0125"),
                reset_frequency=Frequency.QUARTERLY,
                current_reference_rate=Decimal("0.0410"),
            ),
            sector="CORPORATE",
            rating="A",
        ),
    }


def etf_holdings() -> list[EtfHolding]:
    return [
        EtfHolding(FIXED_ID, quantity=Decimal("100")),
        EtfHolding(CALLABLE_ID, quantity=Decimal("80")),
        EtfHolding(FRN_ID, quantity=Decimal("120")),
    ]


def portfolio_positions() -> list[PortfolioPosition]:
    return [
        PortfolioPosition(FIXED_ID, Decimal("100")),
        PortfolioPosition(CALLABLE_ID, Decimal("80")),
        PortfolioPosition(FRN_ID, Decimal("120")),
    ]


def router() -> PricingRouter:
    return PricingRouter()


def pricing_specs() -> tuple[PricingSpec, PricingSpec]:
    fixed = PricingSpec(compute_key_rates=True, include_asset_swap=True)
    floating = PricingSpec(market_price_is_dirty=True)
    return fixed, floating
