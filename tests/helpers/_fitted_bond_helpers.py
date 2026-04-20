from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from fuggers_py._core import Currency, Date, Frequency, InstrumentId, YearMonth
from fuggers_py._runtime.quotes import BondQuote
from fuggers_py._market.snapshot import InflationFixing
from fuggers_py._market.sources import InMemoryInflationFixingSource
from fuggers_py._curves_impl import (
    BondCurveFitter,
    CubicSplineZeroRateCurveModel,
    ExponentialSplineCurveModel,
    BondCurve,
    CurveObjective,
    NominalGovernmentBondPricingAdapter,
    TermStructure,
    TipsRealBondPricingAdapter,
    dirty_price_from_curve,
)
from fuggers_py._curves_impl.fitted_bonds.fair_value import _discount_factor_from_curve
from fuggers_py._products.bonds import FixedBondBuilder, TipsBond
from fuggers_py._products.bonds.traits import Bond
from fuggers_py._core import YieldCalculationRules
from fuggers_py.bonds.types import BondType, IssuerType
from fuggers_py.inflation import USD_CPI_U_NSA
from fuggers_py._reference.reference_data import BondReferenceData


REFERENCE_DATE = Date.from_ymd(2026, 1, 15)
TIPS_REFERENCE_DATE = Date.from_ymd(2026, 1, 15)
CurveModelLike = ExponentialSplineCurveModel | CubicSplineZeroRateCurveModel
UNIVERSE = (
    ("UST2Y", 2, Decimal("0.0200"), Decimal("-1.2"), Decimal("400000000"), Decimal("0.80"), False),
    ("UST3Y", 3, Decimal("0.0225"), Decimal("-0.8"), Decimal("500000000"), Decimal("0.90"), False),
    ("UST4Y", 4, Decimal("0.0250"), Decimal("-0.4"), Decimal("700000000"), Decimal("1.00"), True),
    ("UST5Y", 5, Decimal("0.0275"), Decimal("0.0"), Decimal("900000000"), Decimal("1.10"), True),
    ("UST6Y", 6, Decimal("0.0300"), Decimal("0.4"), Decimal("1100000000"), Decimal("1.15"), True),
    ("UST8Y", 8, Decimal("0.0350"), Decimal("0.8"), Decimal("800000000"), Decimal("1.00"), True),
    ("UST10Y", 10, Decimal("0.0400"), Decimal("1.2"), Decimal("600000000"), Decimal("0.85"), False),
)
TIPS_UNIVERSE = (
    ("TIPS2Y", 2, Decimal("0.0050"), Decimal("-1.0"), Decimal("0.85")),
    ("TIPS3Y", 3, Decimal("0.0060"), Decimal("-0.5"), Decimal("0.95")),
    ("TIPS5Y", 5, Decimal("0.0075"), Decimal("0.0"), Decimal("1.05")),
    ("TIPS7Y", 7, Decimal("0.0090"), Decimal("0.5"), Decimal("1.15")),
    ("TIPS10Y", 10, Decimal("0.0110"), Decimal("1.0"), Decimal("1.25")),
)
LIQUIDITY_BY_ID = {
    instrument_id: exposure_value
    for instrument_id, _, _, exposure_value, *_ in UNIVERSE
}
LIQUIDITY_BY_ID.update(
    {
        instrument_id: exposure_value
        for instrument_id, _, _, exposure_value, *_ in TIPS_UNIVERSE
    }
)


def exponential_model() -> ExponentialSplineCurveModel:
    return ExponentialSplineCurveModel((Decimal("0.40"), Decimal("1.20")))


def cubic_model() -> CubicSplineZeroRateCurveModel:
    return CubicSplineZeroRateCurveModel((Decimal("2.0"), Decimal("4.0"), Decimal("6.0"), Decimal("8.0"), Decimal("10.0")))


def liquidity_regression_exposures(
    quotes: Sequence[BondQuote],
) -> dict[str, tuple[Decimal, ...]]:
    return {
        "liquidity": tuple(LIQUIDITY_BY_ID[quote.instrument_id.as_str()] for quote in quotes)
    }


def observation_regression_exposures(
    quote: BondQuote,
) -> dict[str, Decimal]:
    return {"liquidity": LIQUIDITY_BY_ID[quote.instrument_id.as_str()]}


def nominal_pricing_adapter() -> NominalGovernmentBondPricingAdapter:
    return NominalGovernmentBondPricingAdapter()


def tips_fixing_source() -> InMemoryInflationFixingSource:
    fixings: list[InflationFixing] = []
    year = 2023
    month = 10
    level = Decimal("100.00")
    while (year, month) <= (2036, 12):
        fixings.append(
            InflationFixing(
                index_name="CPURNSA",
                observation_month=YearMonth(year=year, month=month),
                value=level,
            )
        )
        level += Decimal("0.22")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return InMemoryInflationFixingSource(fixings)


def tips_pricing_adapter(
    fixing_source: InMemoryInflationFixingSource | None = None,
) -> TipsRealBondPricingAdapter:
    return TipsRealBondPricingAdapter(fixing_source or tips_fixing_source())


def _curve_parameters_for(model: CurveModelLike) -> NDArray[np.float64]:
    if isinstance(model, ExponentialSplineCurveModel):
        return np.asarray([0.032, -0.008, 0.004], dtype=float)
    if isinstance(model, CubicSplineZeroRateCurveModel):
        return np.asarray([0.024, 0.027, 0.031, 0.034, 0.036], dtype=float)
    raise TypeError(f"Unsupported helper model: {type(model).__name__}.")


def nominal_bond_lookup() -> dict[str, Bond]:
    bonds: dict[str, Bond] = {}
    for instrument_id, maturity_years, coupon_rate, *_ in UNIVERSE:
        resolved_instrument_id = InstrumentId(instrument_id)
        bonds[instrument_id] = (
            FixedBondBuilder.new()
            .with_issue_date(Date.from_ymd(2021, 1, 15))
            .with_maturity_date(REFERENCE_DATE.add_years(maturity_years))
            .with_coupon_rate(coupon_rate)
            .with_frequency(Frequency.SEMI_ANNUAL)
            .with_currency(Currency.USD)
            .with_instrument_id(resolved_instrument_id)
            .with_rules(YieldCalculationRules.us_treasury())
            .build()
        )
    return bonds


def nominal_reference_data_lookup() -> dict[str, BondReferenceData]:
    reference_data: dict[str, BondReferenceData] = {}
    for (
        instrument_id,
        maturity_years,
        coupon_rate,
        _exposure_value,
        amount_outstanding,
        liquidity_score,
        benchmark_flag,
    ) in UNIVERSE:
        resolved_instrument_id = InstrumentId(instrument_id)
        reference_data[instrument_id] = BondReferenceData(
            instrument_id=resolved_instrument_id,
            bond_type=BondType.FIXED_RATE,
            issuer_type=IssuerType.SOVEREIGN,
            issue_date=Date.from_ymd(2021, 1, 15),
            maturity_date=REFERENCE_DATE.add_years(maturity_years),
            currency=Currency.USD,
            coupon_rate=coupon_rate,
            frequency=Frequency.SEMI_ANNUAL,
            amount_outstanding=amount_outstanding,
            benchmark_flag=benchmark_flag,
            futures_deliverable_flags=("USTFUT",) if maturity_years in {6, 8} else (),
            liquidity_score=liquidity_score,
        )
    return reference_data


def tips_bond_lookup() -> dict[str, Bond]:
    bonds: dict[str, Bond] = {}
    for instrument_id, maturity_years, coupon_rate, *_ in TIPS_UNIVERSE:
        resolved_instrument_id = InstrumentId(instrument_id)
        bonds[instrument_id] = TipsBond.new(
            issue_date=Date.from_ymd(2024, 1, 15),
            dated_date=Date.from_ymd(2024, 1, 15),
            maturity_date=TIPS_REFERENCE_DATE.add_years(maturity_years),
            coupon_rate=coupon_rate,
            inflation_convention=USD_CPI_U_NSA,
            base_reference_date=Date.from_ymd(2024, 1, 15),
            frequency=Frequency.SEMI_ANNUAL,
            currency=Currency.USD,
            instrument_id=resolved_instrument_id,
        )
    return bonds


def nominal_fit_kwargs(
    *,
    weights: Mapping[str, Decimal] | None = None,
) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "reference_data": nominal_reference_data_lookup(),
    }
    if weights is not None:
        kwargs["weights"] = weights
    return kwargs


def tips_fit_kwargs(
    *,
    weights: Mapping[str, Decimal] | None = None,
) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if weights is not None:
        kwargs["weights"] = weights
    return kwargs


def make_observations(
    *,
    curve_model: CurveModelLike | None = None,
    regression_coefficient: Decimal = Decimal("0"),
    mispricings: dict[str, Decimal] | None = None,
    weights: dict[str, Decimal] | None = None,
    quote_field: str = "clean",
) -> tuple[tuple[BondQuote, ...], TermStructure]:
    del weights
    model = curve_model or exponential_model()
    curve = model.build_term_structure(REFERENCE_DATE, _curve_parameters_for(model), max_t=10.0)
    bonds = nominal_bond_lookup()
    quotes: list[BondQuote] = []
    for instrument_id, _maturity_years, _coupon_rate, exposure_value, *_ in UNIVERSE:
        bond = bonds[instrument_id]
        curve_dirty = dirty_price_from_curve(bond, curve, REFERENCE_DATE)
        regression_adjustment = regression_coefficient * exposure_value
        mispricing = (mispricings or {}).get(instrument_id, Decimal(0))
        observed_dirty = curve_dirty + regression_adjustment + mispricing
        clean_price = observed_dirty - bond.accrued_interest(REFERENCE_DATE)
        quotes.append(
            BondQuote(
                instrument=bond,
                dirty_price=observed_dirty if quote_field == "dirty" else None,
                clean_price=None if quote_field == "dirty" else clean_price,
                as_of=REFERENCE_DATE,
            )
        )
    return tuple(quotes), curve


def _tips_dirty_price_from_curve(
    bond: TipsBond,
    curve: TermStructure,
    settlement_date: Date,
    fixing_source: InMemoryInflationFixingSource,
) -> Decimal:
    present_value = Decimal(0)
    for cash_flow in bond.projected_cash_flows(
        fixing_source=fixing_source,
        settlement_date=settlement_date,
    ):
        present_value += cash_flow.factored_amount() * _discount_factor_from_curve(curve, cash_flow.date)
    return present_value


def make_curve_observations(
    *,
    curve_model: CurveModelLike | None = None,
    regression_coefficient: Decimal = Decimal("0"),
    mispricings: dict[str, Decimal] | None = None,
    weights: dict[str, Decimal] | None = None,
    quote_field: str = "clean",
) -> tuple[tuple[BondQuote, ...], TermStructure]:
    return make_observations(
        curve_model=curve_model,
        regression_coefficient=regression_coefficient,
        mispricings=mispricings,
        weights=weights,
        quote_field=quote_field,
    )


def make_tips_curve_observations(
    *,
    curve_model: CurveModelLike | None = None,
    regression_coefficient: Decimal = Decimal("0"),
    mispricings: dict[str, Decimal] | None = None,
    weights: dict[str, Decimal] | None = None,
) -> tuple[tuple[BondQuote, ...], TermStructure, InMemoryInflationFixingSource]:
    del weights
    model = curve_model or exponential_model()
    curve = model.build_term_structure(TIPS_REFERENCE_DATE, _curve_parameters_for(model), max_t=10.0)
    fixing_source = tips_fixing_source()
    bonds = tips_bond_lookup()
    quotes: list[BondQuote] = []
    for instrument_id, _maturity_years, _coupon_rate, exposure_value, _liquidity_score in TIPS_UNIVERSE:
        bond = bonds[instrument_id]
        assert isinstance(bond, TipsBond)
        curve_dirty = _tips_dirty_price_from_curve(bond, curve, TIPS_REFERENCE_DATE, fixing_source)
        regression_adjustment = regression_coefficient * exposure_value
        mispricing = (mispricings or {}).get(instrument_id, Decimal(0))
        observed_dirty = curve_dirty + regression_adjustment + mispricing
        clean_price = observed_dirty - bond.accrued_interest(TIPS_REFERENCE_DATE, fixing_source=fixing_source)
        quotes.append(
            BondQuote(
                instrument=bond,
                clean_price=clean_price,
                as_of=TIPS_REFERENCE_DATE,
            )
        )
    return tuple(quotes), curve, fixing_source


def fit_result(
    *,
    curve_model: CurveModelLike | None = None,
    objective: CurveObjective = CurveObjective.L2,
    regression_coefficient: Decimal = Decimal("0.25"),
    mispricings: dict[str, Decimal] | None = None,
    weights: dict[str, Decimal] | None = None,
    regression_exposures: Mapping[str, Sequence[object]] | None = None,
) -> BondCurve:
    quotes, _ = make_observations(
        curve_model=curve_model,
        regression_coefficient=regression_coefficient,
        mispricings=mispricings,
        weights=weights,
    )
    return BondCurve(
        quotes,
        shape=curve_model or exponential_model(),
        objective=objective,
        weights=weights,
        reference_data=nominal_reference_data_lookup(),
        regressors=(
            regression_exposures
            if regression_exposures is not None
            else liquidity_regression_exposures(quotes)
        ),
    )


def tips_fit_result(
    *,
    curve_model: CurveModelLike | None = None,
    objective: CurveObjective = CurveObjective.L2,
    regression_coefficient: Decimal = Decimal("0"),
    mispricings: dict[str, Decimal] | None = None,
    weights: dict[str, Decimal] | None = None,
    regression_exposures: Mapping[str, Sequence[object]] | None = None,
) -> BondCurve:
    quotes, _, fixing_source = make_tips_curve_observations(
        curve_model=curve_model,
        regression_coefficient=regression_coefficient,
        mispricings=mispricings,
        weights=weights,
    )
    fitter = BondCurveFitter(
        curve_model=curve_model or exponential_model(),
        objective=objective,
        pricing_adapter=tips_pricing_adapter(fixing_source),
    )
    return fitter.fit(
        quotes,
        weights=weights,
        regression_exposures={} if regression_exposures is None else regression_exposures,
    )
