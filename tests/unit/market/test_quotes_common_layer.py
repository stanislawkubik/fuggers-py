from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Currency, CurrencyPair, Date, Frequency, InstrumentId, YearMonth
from fuggers_py.market.quotes import (
    BasisSwapQuote,
    BondFutureQuote,
    BondQuote,
    CdsQuote,
    deliverable_bpv_regressor,
    FxForwardQuote,
    HaircutQuote,
    InstrumentQuote,
    RawQuote,
    RepoQuote,
    ScalarQuote,
    SwapQuote,
)
from fuggers_py.market.snapshot import CurveInput, CurveInstrumentType, MarketDataSnapshot
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.reference.bonds.types import YieldCalculationRules


def _sample_bond(instrument_id: str) -> object:
    return (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 15))
        .with_maturity_date(Date.from_ymd(2029, 1, 15))
        .with_coupon_rate(Decimal("0.045"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_instrument_id(instrument_id)
        .with_rules(YieldCalculationRules.us_treasury())
        .build()
    )


def test_scalar_quote_is_the_canonical_raw_quote_alias() -> None:
    quote = ScalarQuote(
        instrument_id="RAW-1",
        value="101.25",
        as_of=Date.from_ymd(2026, 4, 6),
        currency=Currency.USD,
        source="screen",
    )

    assert type(quote) is RawQuote
    assert isinstance(quote, ScalarQuote)
    assert quote == RawQuote(
        instrument_id="RAW-1",
        value=Decimal("101.25"),
        as_of=Date.from_ymd(2026, 4, 6),
        currency=Currency.USD,
        source="screen",
    )


def test_quote_families_conform_to_common_instrument_quote_protocol() -> None:
    as_of = Date.from_ymd(2026, 4, 6)
    bond = _sample_bond("BOND-1")
    quotes = (
        RawQuote("RAW-1", Decimal("101.25"), as_of=as_of, currency=Currency.USD, source="raw"),
        BondQuote(instrument=bond, clean_price=Decimal("100.50"), as_of=as_of, source="bond"),
        RepoQuote("REPO-1", rate=Decimal("0.045"), as_of=as_of, currency=Currency.USD, source="repo"),
        SwapQuote("SWAP-1", rate=Decimal("0.039"), as_of=as_of, currency=Currency.USD, source="swap"),
        BasisSwapQuote("BASIS-1", basis=Decimal("0.0012"), as_of=as_of, currency=Currency.USD, source="basis"),
        BondFutureQuote(
            "FUT-1",
            price=Decimal("112.50"),
            delivery_month=YearMonth(2026, 6),
            as_of=as_of,
            currency=Currency.USD,
            source="future",
        ),
        FxForwardQuote(
            currency_pair=CurrencyPair.parse("EUR/USD"),
            forward_rate=Decimal("1.09"),
            as_of=as_of,
            source="fxfwd",
        ),
        CdsQuote("CDS-1", par_spread=Decimal("0.0125"), as_of=as_of, currency=Currency.USD, source="cds"),
        HaircutQuote("HAIRCUT-1", haircut=Decimal("0.02"), as_of=as_of, currency=Currency.USD, source="haircut"),
    )

    for quote in quotes:
        assert isinstance(quote, InstrumentQuote)

    fx_forward = quotes[6]
    assert fx_forward.instrument_id == InstrumentId("EUR/USD")
    assert fx_forward.currency is Currency.USD


def test_curve_input_quote_annotation_is_widened_and_accepts_bond_quotes() -> None:
    bond = _sample_bond("BOND-2")
    quote = BondQuote(
        instrument=bond,
        clean_price=Decimal("99.75"),
        as_of=Date.from_ymd(2026, 4, 6),
        source="bond",
    )
    curve_input = CurveInput(
        instrument_type=CurveInstrumentType.BOND,
        instrument_id="BOND-2",
        price=Decimal("99.75"),
        quote=quote,
    )

    assert "AnyInstrumentQuote" in str(CurveInput.__annotations__["quote"])
    assert curve_input.quote == quote
    assert isinstance(curve_input.quote, InstrumentQuote)


def test_bond_quote_keeps_optional_regressors_and_fit_weight_on_the_quote() -> None:
    bond = _sample_bond("BOND-3")
    quote = BondQuote(
        instrument=bond,
        clean_price=Decimal("99.25"),
        as_of=Date.from_ymd(2026, 4, 6),
        regressors={"liquidity": Decimal("0.25"), "seasonality": 1},
        fit_weight=Decimal("2.5"),
    )

    assert quote.regressors == {"liquidity": 0.25, "seasonality": 1.0}
    assert quote.fit_weight == 2.5


def test_bond_quote_rejects_invalid_regressors_and_fit_weight() -> None:
    bond = _sample_bond("BOND-4")

    try:
        BondQuote(
            instrument=bond,
            clean_price=Decimal("99.25"),
            as_of=Date.from_ymd(2026, 4, 6),
            regressors={"liquidity": float("nan")},
        )
    except ValueError as exc:
        assert "BondQuote.regressors" in str(exc)
    else:
        raise AssertionError("BondQuote should reject non-finite regressor values.")

    try:
        BondQuote(
            instrument=bond,
            clean_price=Decimal("99.25"),
            as_of=Date.from_ymd(2026, 4, 6),
            fit_weight=float("inf"),
        )
    except ValueError as exc:
        assert "BondQuote.fit_weight" in str(exc)
    else:
        raise AssertionError("BondQuote should reject non-finite fit weights.")


def test_deliverable_bpv_regressor_encodes_non_deliverable_bonds_as_zero() -> None:
    assert deliverable_bpv_regressor(12.5, deliverable=True) == 12.5
    assert deliverable_bpv_regressor(12.5, deliverable=False) == 0.0

    try:
        deliverable_bpv_regressor(float("nan"), deliverable=True)
    except ValueError as exc:
        assert "bpv" in str(exc)
    else:
        raise AssertionError("deliverable_bpv_regressor should reject non-finite bpv values.")


def test_market_data_snapshot_flattens_instrument_quotes_in_family_order() -> None:
    as_of = Date.from_ymd(2026, 4, 6)
    raw_quote = RawQuote("RAW-3", Decimal("100.10"), as_of=as_of, currency=Currency.USD)
    repo_quote = RepoQuote("REPO-3", rate=Decimal("0.043"), as_of=as_of, currency=Currency.USD)
    swap_quote = SwapQuote("SWAP-3", rate=Decimal("0.038"), as_of=as_of, currency=Currency.USD)
    basis_quote = BasisSwapQuote("BASIS-3", basis=Decimal("0.0009"), as_of=as_of, currency=Currency.USD)
    future_quote = BondFutureQuote(
        "FUT-3",
        price=Decimal("113.20"),
        delivery_month=YearMonth(2026, 9),
        as_of=as_of,
        currency=Currency.USD,
    )
    fx_forward_quote = FxForwardQuote(
        currency_pair="GBP/USD",
        forward_rate=Decimal("1.255"),
        as_of=as_of,
        source="fx",
    )
    cds_quote = CdsQuote("CDS-3", par_spread=Decimal("0.011"), as_of=as_of, currency=Currency.USD)
    haircut_quote = HaircutQuote("HAIRCUT-3", haircut=Decimal("0.015"), as_of=as_of, currency=Currency.USD)
    snapshot = MarketDataSnapshot(
        as_of=as_of,
        quotes=(raw_quote,),
        repo_quotes=(repo_quote,),
        swap_quotes=(swap_quote,),
        basis_swap_quotes=(basis_quote,),
        bond_future_quotes=(future_quote,),
        fx_forward_quotes=(fx_forward_quote,),
        cds_quotes=(cds_quote,),
        haircut_quotes=(haircut_quote,),
    )

    assert snapshot.instrument_quotes() == (
        raw_quote,
        repo_quote,
        swap_quote,
        basis_quote,
        future_quote,
        fx_forward_quote,
        cds_quote,
        haircut_quote,
    )


def test_snapshot_provider_keeps_scalar_quote_path_unchanged() -> None:
    as_of = Date.from_ymd(2026, 4, 6)
    raw_quote = RawQuote("RAW-4", Decimal("99.90"), as_of=as_of, currency=Currency.USD)
    repo_quote = RepoQuote("REPO-4", rate=Decimal("0.041"), as_of=as_of, currency=Currency.USD)
    snapshot = MarketDataSnapshot(
        as_of=as_of,
        quotes=(raw_quote,),
        repo_quotes=(repo_quote,),
    )

    provider = snapshot.provider()

    assert snapshot.instrument_quotes() == (raw_quote, repo_quote)
    assert provider.get_quote("RAW-4") == raw_quote
    assert provider.get_quote("REPO-4") is None
