from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import Currency, Date
from fuggers_py._runtime import QuoteSide
from fuggers_py._core import CurrencyPair, CurveId, EtfId, InstrumentId, VolSurfaceId, YearMonth
from fuggers_py._runtime.quotes import (
    BasisSwapQuote,
    BondFutureQuote,
    CdsQuote,
    FxForwardQuote,
    HaircutQuote,
    RawQuote,
    RepoQuote,
    SwapQuote,
)
from fuggers_py._runtime.snapshot import (
    CurveInput,
    CurveInputs,
    CurveInstrumentType,
    CurvePoint,
    EtfQuote,
    FxRate,
    IndexFixing,
    InflationFixing,
    MarketDataSnapshot,
)
from fuggers_py._runtime.sources import (
    CurveInputSource,
    FxRateSource,
    InMemoryCurveSource,
    InMemoryEtfQuoteSource,
    InMemoryFixingSource,
    InMemoryFxRateSource,
    InMemoryInflationFixingSource,
    InMemoryQuoteSource,
    MarketDataProvider,
    PricingDataProvider,
    QuoteSource,
)
from fuggers_py.vol_surfaces import InMemoryVolatilitySource, VolPoint, VolSurfaceType, VolatilitySource, VolatilitySurface


def test_in_memory_market_data_provider_serves_extended_sources() -> None:
    as_of = Date.from_ymd(2026, 3, 13)
    quote = RawQuote(
        instrument_id=InstrumentId("BOND-1"),
        value=Decimal("101.25"),
        as_of=as_of,
        currency=Currency.USD,
        bid=Decimal("101.10"),
        ask=Decimal("101.40"),
        source="dealer-run",
    )
    curve_inputs = CurveInputs.from_points(
        CurveId("usd.discount"),
        as_of,
        [
            CurvePoint(Decimal("5.0"), Decimal("0.0390")),
            CurvePoint(Decimal("1.0"), Decimal("0.0425")),
        ],
        instruments=[
            CurveInput(
                instrument_type=CurveInstrumentType.BOND,
                instrument_id=InstrumentId("BOND-1"),
                tenor=Decimal("5.0"),
                rate=Decimal("0.0390"),
            )
        ],
    )
    fixing = IndexFixing("SOFR", as_of, Decimal("0.0410"))
    surface = VolatilitySurface(
        surface_id=VolSurfaceId("usd.swaption"),
        surface_type=VolSurfaceType.SWAPTION,
        as_of=as_of,
        points=(VolPoint(expiry=YearMonth(2026, 6), tenor=YearMonth(2028, 6), strike=Decimal("0.03"), volatility=Decimal("0.22")),),
    )
    fx_rate = FxRate(
        currency_pair=CurrencyPair.parse("usd/eur"),
        rate=Decimal("0.9200"),
        bid=Decimal("0.9190"),
        ask=Decimal("0.9210"),
        as_of=as_of,
    )
    inflation = InflationFixing("CPI", YearMonth.parse("2026-02"), Decimal("307.12"))
    etf_quote = EtfQuote(etf_id=EtfId("agg-usd"), market_price=Decimal("101.20"), nav=Decimal("101.10"), as_of=as_of)

    provider = MarketDataProvider(
        quote_source=InMemoryQuoteSource([quote]),
        curve_input_source=InMemoryCurveSource([curve_inputs]),
        index_fixing_source=InMemoryFixingSource([fixing]),
        volatility_source=InMemoryVolatilitySource([surface]),
        fx_rate_source=InMemoryFxRateSource([fx_rate]),
        inflation_fixing_source=InMemoryInflationFixingSource([inflation]),
        etf_quote_source=InMemoryEtfQuoteSource([etf_quote]),
    )

    assert isinstance(provider, QuoteSource)
    assert isinstance(provider, CurveInputSource)
    assert isinstance(provider, PricingDataProvider)
    assert isinstance(provider, VolatilitySource)
    assert isinstance(provider, FxRateSource)
    assert provider.get_quote("BOND-1", QuoteSide.BID).value == Decimal("101.10")
    assert provider.get_curve_inputs("usd.discount") == curve_inputs
    assert provider.get_fixing("SOFR", as_of) == fixing
    assert provider.get_volatility_surface("usd.swaption") == surface
    assert provider.get_fx_rate("usd/eur", QuoteSide.ASK).rate == Decimal("0.9210")
    assert provider.get_inflation_fixing("CPI", "2026-02") == inflation
    assert provider.get_etf_quote("agg-usd") == etf_quote


def test_market_data_snapshot_builds_composite_provider() -> None:
    as_of = Date.from_ymd(2026, 3, 13)
    snapshot = MarketDataSnapshot(
        as_of=as_of,
        quotes=(RawQuote(InstrumentId("BOND-2"), Decimal("99.50"), as_of=as_of),),
        fx_rates=(FxRate(CurrencyPair.parse("eur/usd"), Decimal("1.09"), as_of=as_of),),
    )

    provider = snapshot.provider()

    assert provider.get_quote("BOND-2") is not None
    assert provider.get_fx_rate("EUR/USD") is not None


def test_extended_quote_records_coerce_decimals_and_normalize_fields() -> None:
    as_of = Date.from_ymd(2026, 3, 13)

    repo = RepoQuote(
        instrument_id="repo-usd-1w",
        rate="0.0415",
        haircut="0.02",
        term=" 1w ",
        collateral_type=" UST ",
        as_of=as_of,
    )
    swap = SwapQuote(
        instrument_id="usd-swap-5y",
        rate="0.0380",
        tenor=" 5y ",
        floating_index=" sofr ",
        fixed_frequency=" semi_annual ",
        bid="0.0380",
        as_of=as_of,
    )
    basis = BasisSwapQuote(
        instrument_id="usd-basis-5y",
        basis="0.0012",
        tenor=" 5y ",
        pay_index=" sofr ",
        receive_index=" libor_3m ",
        ask="0.0012",
        as_of=as_of,
    )
    future = BondFutureQuote(
        instrument_id="ust-mar26",
        price="112.5",
        delivery_month="2026-03",
        conversion_factor="0.8125",
        cheapest_to_deliver="US91282CKH3",
        as_of=as_of,
    )
    fx_forward = FxForwardQuote(
        currency_pair="eur/usd",
        spot_rate="1.08",
        points="0.015",
        as_of=as_of,
    )
    cds = CdsQuote(
        instrument_id="acme-cds-5y",
        par_spread="0.0125",
        recovery_rate="0.4",
        tenor=" 5y ",
        reference_entity=" ACME Corp ",
        as_of=as_of,
    )
    haircut = HaircutQuote(
        instrument_id="ust-on-the-run",
        haircut="0.015",
        collateral_type=" govies ",
        as_of=as_of,
    )

    assert repo.instrument_id == InstrumentId("repo-usd-1w")
    assert repo.rate == Decimal("0.0415")
    assert repo.haircut == Decimal("0.02")
    assert repo.term == "1W"
    assert repo.mid == Decimal("0.0415")

    assert swap.floating_index == "SOFR"
    assert swap.fixed_frequency == "SEMI_ANNUAL"
    assert swap.bid == Decimal("0.0380")
    assert swap.for_side(QuoteSide.BID) == swap

    assert basis.receive_index == "LIBOR_3M"
    assert basis.ask == Decimal("0.0012")

    assert future.delivery_month == YearMonth(2026, 3)
    assert future.cheapest_to_deliver == InstrumentId("US91282CKH3")
    assert future.conversion_factor == Decimal("0.8125")

    assert fx_forward.currency_pair == CurrencyPair.parse("EUR/USD")
    assert fx_forward.forward_rate == Decimal("1.095")
    assert fx_forward.mid == Decimal("1.095")

    assert cds.par_spread == Decimal("0.0125")
    assert cds.recovery_rate == Decimal("0.4")
    assert cds.reference_entity == "ACME Corp"
    assert cds.mid == Decimal("0.0125")

    assert haircut.collateral_type == "govies"
    assert haircut.haircut == Decimal("0.015")
    assert haircut.mid == Decimal("0.015")


def test_curve_input_accepts_extended_quote_records() -> None:
    quote = SwapQuote(
        instrument_id="usd-swap-10y",
        rate="0.0395",
        floating_index="sofr",
    )
    curve_input = CurveInput(
        instrument_type=CurveInstrumentType.SWAP,
        instrument_id="usd-swap-10y",
        tenor="10.0",
        rate="0.0395",
        quote=quote,
        label=" USD swap 10Y ",
    )

    assert curve_input.instrument_type is CurveInstrumentType.SWAP
    assert curve_input.instrument_id == InstrumentId("usd-swap-10y")
    assert curve_input.tenor == Decimal("10.0")
    assert curve_input.quote == quote
    assert curve_input.label == "USD swap 10Y"
