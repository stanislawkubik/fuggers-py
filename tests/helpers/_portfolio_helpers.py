from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py.bonds.instruments import CallableBondBuilder, FixedBond, FloatingRateNoteBuilder
from fuggers_py.rates import BondIndex, IndexConventions, IndexFixingStore, OvernightCompounding
from fuggers_py.bonds.types import CreditRating, RatingInfo, RateIndex, Sector, SectorInfo
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._runtime.snapshot import CurvePoint
from fuggers_py.portfolio import Classification, Holding, Portfolio, PortfolioBuilder
from tests.helpers._public_curve_helpers import linear_zero_curve


def make_curve(ref: Date, *, shift: Decimal = Decimal(0)):
    return linear_zero_curve(
        "portfolio.discount",
        ref,
        (
            CurvePoint(Decimal("0.5"), Decimal("0.03") + shift),
            CurvePoint(Decimal("2.0"), Decimal("0.0325") + shift),
            CurvePoint(Decimal("5.0"), Decimal("0.0350") + shift),
            CurvePoint(Decimal("10.0"), Decimal("0.04") + shift),
        ),
        curve_type="overnight_discount",
    )


def annual_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL)


def make_fixed_bond(ref: Date, *, years: int, coupon: str) -> FixedBond:
    return FixedBond.new(
        issue_date=ref,
        maturity_date=ref.add_years(years),
        coupon_rate=Decimal(coupon),
        frequency=Frequency.ANNUAL,
        currency=Currency.USD,
        rules=annual_rules(),
    )


def make_holding(
    ref: Date,
    *,
    years: int,
    coupon: str,
    label: str,
    sector: Sector,
    rating: CreditRating,
    quantity: str = "100",
    price: str = "100",
) -> Holding:
    bond = make_fixed_bond(ref, years=years, coupon=coupon)
    return Holding(
        id=label,
        instrument=bond,
        quantity=Decimal(quantity),
        clean_price=Decimal(price),
        label=label,
        classification=Classification(sector=sector, rating=rating, currency=Currency.USD, issuer=f"{label}_issuer"),
        rating_info=RatingInfo(rating=rating),
        sector_info=SectorInfo(sector=sector, issuer=f"{label}_issuer", country="US", region="NA"),
        liquidity_score=Decimal("0.85"),
    )


def make_portfolio(ref: Date) -> Portfolio:
    return (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_holding(make_holding(ref, years=2, coupon="0.035", label="gov_short", sector=Sector.GOVERNMENT, rating=CreditRating.AA, price="99.5"))
        .add_holding(make_holding(ref, years=5, coupon="0.05", label="corp_bbb", sector=Sector.CORPORATE, rating=CreditRating.BBB, price="101.0"))
        .add_holding(make_holding(ref, years=8, coupon="0.0625", label="corp_bb", sector=Sector.INDUSTRIALS, rating=CreditRating.BB, price="98.0"))
        .build()
    )


def make_benchmark(ref: Date) -> Portfolio:
    return (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_holding(make_holding(ref, years=3, coupon="0.03", label="bench_gov", sector=Sector.GOVERNMENT, rating=CreditRating.A, price="100.5"))
        .add_holding(make_holding(ref, years=6, coupon="0.045", label="bench_corp", sector=Sector.CORPORATE, rating=CreditRating.BBB, price="100.0"))
        .build()
    )


def make_frn(ref: Date) -> tuple[object, IndexFixingStore]:
    store = IndexFixingStore()
    start = ref.add_days(-10)
    for offset, rate in enumerate(["0.049", "0.0495", "0.050", "0.0505", "0.051", "0.0515", "0.052", "0.0525"], start=0):
        store.add_fixing("SOFR", start.add_days(offset), Decimal(rate))
    index = BondIndex(
        name="SOFR",
        rate_index=RateIndex.SOFR,
        currency=Currency.USD,
        fixing_store=store,
        conventions=IndexConventions(overnight_compounding=OvernightCompounding.COMPOUNDED),
    )
    frn = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(ref.add_months(-3))
        .with_maturity_date(ref.add_years(2))
        .with_index(RateIndex.SOFR)
        .with_index_definition(index)
        .with_frequency(Frequency.QUARTERLY)
        .with_rules(replace(YieldCalculationRules.us_treasury(), frequency=Frequency.QUARTERLY))
        .with_current_reference_rate(Decimal("0.052"))
        .with_quoted_spread(Decimal("0.0025"))
        .build()
    )
    return frn, store


def make_callable_puttable(ref: Date):
    base = make_fixed_bond(ref, years=7, coupon="0.055")
    return (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(call_date=ref.add_years(3), call_price=Decimal("101.0"))
        .add_put(put_date=ref.add_years(2), put_price=Decimal("102.0"))
        .build()
    )
