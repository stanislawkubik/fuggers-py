from __future__ import annotations

import json
import re
from dataclasses import replace
from decimal import Decimal, getcontext
from functools import lru_cache
from typing import Any

import numpy as np
import pytest

from fuggers_py.bonds.analytics_pricing import BondPricer
from fuggers_py.bonds.spreads import DiscountMarginCalculator, OASCalculator
from fuggers_py.bonds.cashflows import AccruedInterestCalculator, AccruedInterestInputs
from fuggers_py.rates import BondIndex, IndexConventions, IndexFixingStore, ObservationShiftType, OvernightCompounding
from fuggers_py.bonds.instruments import CallableBondBuilder, CallType, FixedBond, FloatingRateNoteBuilder, ZeroCouponBond
from fuggers_py.bonds.options import HullWhiteModel
from fuggers_py.bonds.types import CreditRating, PutType, RateIndex, RatingInfo, Sector, SectorInfo
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Compounding, Currency, Date, Frequency, Yield
from fuggers_py._runtime.snapshot import CurvePoint
from fuggers_py.curves import CalibrationReport, CurveSpec, YieldCurve
from fuggers_py.curves.conversion import ValueConverter
from fuggers_py.portfolio import PortfolioAnalyzer, PortfolioPosition
from fuggers_py.portfolio import AttributionInput, Classification, Holding, PortfolioBuilder, aggregated_attribution, benchmark_comparison
from fuggers_py._core.ids import InstrumentId, PortfolioId
from fuggers_py._runtime.output import BondQuoteOutput
from fuggers_py.bonds.types import BondType, IssuerType
from fuggers_py.bonds.reference_data import BondReferenceData
from fuggers_py.rates import SwapQuote

from tests.helpers._paths import FIXTURES_ROOT
from tests.helpers._public_curve_helpers import linear_zero_curve, log_linear_discount_curve
from tests.helpers._rates_helpers import flat_curve

from ._helpers import D, assert_decimal_close, parse_date


getcontext().prec = 50

FIXTURE_PATH = FIXTURES_ROOT / "golden" / "validation_corpus.json"
EXPECTED_CASE_IDS = [
    "fixed_rate_bullet",
    "zero_coupon",
    "accrued_interest_ex_dividend",
    "callable_oas_effective_duration",
    "floating_rate_note_discount_margin",
    "callable_workout_behavior",
    "frn_fixing_lookback_coupon",
    "curve_conversion_interpolation",
    "curve_global_fit_nelson_siegel",
    "portfolio_weighted_metrics",
    "portfolio_benchmark_attribution",
]


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return D(value)


def _ns_zero(t: float, beta0: float, beta1: float, beta2: float, tau: float) -> float:
    if t <= 0.0:
        return beta0 + beta1
    x = t / tau
    exp_x = np.exp(-x)
    factor = (1.0 - exp_x) / x
    return float(beta0 + beta1 * factor + beta2 * (factor - exp_x))


def _yield_rules(name: str, frequency: Frequency) -> YieldCalculationRules:
    if name == "us_treasury":
        rules = YieldCalculationRules.us_treasury()
    elif name == "us_corporate":
        rules = YieldCalculationRules.us_corporate()
    elif name == "uk_gilt":
        rules = YieldCalculationRules.uk_gilt()
    else:
        raise AssertionError(f"Unsupported rules name in validation corpus: {name}")
    if rules.frequency is frequency:
        return rules
    return replace(rules, frequency=frequency)


@lru_cache(maxsize=1)
def _load_corpus() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _cases_by_id() -> dict[str, dict[str, Any]]:
    corpus = _load_corpus()
    return {str(case["id"]): case for case in corpus["cases"]}


def _compute_fixed_rate_bullet(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    frequency = Frequency[inputs["frequency"]]
    bond = FixedBond.new(
        issue_date=parse_date(inputs["issue_date"]),
        maturity_date=parse_date(inputs["maturity_date"]),
        coupon_rate=D(inputs["coupon_rate"]),
        frequency=frequency,
        currency=Currency.USD,
        rules=_yield_rules(inputs["convention"], frequency),
    )
    ytm = Yield.new(D(inputs["yield_to_maturity"]), Compounding[inputs["frequency"]])
    price = BondPricer().price_from_yield(bond, ytm, parse_date(inputs["settlement_date"]))
    return {
        "clean_price_from_yield": price.clean.as_percentage(),
        "dirty_price_from_yield": price.dirty.as_percentage(),
    }


def _compute_zero_coupon(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    reference_date = parse_date(inputs["reference_date"])
    bond = ZeroCouponBond(
        _issue_date=parse_date(inputs["issue_date"]),
        _maturity_date=parse_date(inputs["maturity_date"]),
        _currency=Currency.USD,
        _notional=Decimal("100"),
        _rules=YieldCalculationRules.us_treasury(),
    )
    max_cashflow_tenor = max(
        Decimal(reference_date.days_between(cashflow.date)) / Decimal(365)
        for cashflow in bond.cash_flows()
    )
    curve = log_linear_discount_curve(
        "corpus.zero-coupon",
        reference_date,
        tuple(
            CurvePoint(D(pillar["tenor_years"]), D(pillar["discount_factor"]))
            for pillar in inputs["discount_curve_pillars"]
        ),
        extend_last_discount_factor_to=max_cashflow_tenor,
    )
    price = BondPricer().price_from_curve(bond, curve, reference_date)
    return {"clean_price_from_curve": price.clean.as_percentage()}


def _compute_accrued_interest_ex_dividend(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    entry = AccruedInterestInputs(
        settlement_date=parse_date(inputs["settlement_date"]),
        accrual_start=parse_date(inputs["accrual_start"]),
        accrual_end=parse_date(inputs["accrual_end"]),
        coupon_amount=D(inputs["coupon_amount"]),
        coupon_date=parse_date(inputs["coupon_date"]),
        full_coupon_amount=D(inputs["full_coupon_amount"]),
        period_start=parse_date(inputs["period_start"]),
        period_end=parse_date(inputs["period_end"]),
    )
    rules = _yield_rules(inputs["convention"], Frequency[inputs["frequency"]])
    return {
        "standard_accrued_interest": AccruedInterestCalculator.standard(entry, rules=rules),
        "ex_dividend_accrued_interest": AccruedInterestCalculator.ex_dividend(entry, rules=rules),
    }


def _compute_callable_oas(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    frequency = Frequency[inputs["frequency"]]
    base = FixedBond.new(
        issue_date=parse_date(inputs["issue_date"]),
        maturity_date=parse_date(inputs["maturity_date"]),
        coupon_rate=D(inputs["coupon_rate"]),
        frequency=frequency,
        currency=Currency.USD,
        rules=_yield_rules(inputs["convention"], frequency),
    )
    builder = CallableBondBuilder.new().with_base_bond(base)
    call_type = CallType[inputs["call_type"]]
    for entry in inputs["call_schedule"]:
        builder = builder.add_call(
            call_date=parse_date(entry["call_date"]),
            call_price=D(entry["call_price"]),
            call_type=call_type,
        )
    callable_bond = builder.build()

    curve = flat_curve(parse_date(inputs["curve_reference_date"]), D(inputs["flat_zero_rate"]))
    model = HullWhiteModel(
        mean_reversion=D(inputs["mean_reversion"]),
        volatility=D(inputs["volatility"]),
        term_structure=curve,
    )
    calculator = OASCalculator(model=model)
    settlement = parse_date(inputs["settlement_date"])
    oas = D(inputs["oas_decimal"])
    return {
        "market_dirty_price": calculator.price_with_oas(callable_bond, oas, settlement),
        "effective_duration": calculator.effective_duration(callable_bond, oas, settlement),
    }


def _compute_callable_workout_behavior(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    frequency = Frequency[inputs["frequency"]]
    base = FixedBond.new(
        issue_date=parse_date(inputs["issue_date"]),
        maturity_date=parse_date(inputs["maturity_date"]),
        coupon_rate=D(inputs["coupon_rate"]),
        frequency=frequency,
        currency=Currency.USD,
        rules=_yield_rules(inputs["convention"], frequency),
    )
    builder = CallableBondBuilder.new().with_base_bond(base)
    for entry in inputs["call_schedule"]:
        builder = builder.add_call(
            call_date=parse_date(entry["call_date"]),
            call_price=D(entry["call_price"]),
            call_type=CallType[entry.get("call_type", "EUROPEAN")],
        )
    for entry in inputs["put_schedule"]:
        builder = builder.add_put(
            put_date=parse_date(entry["put_date"]),
            put_price=D(entry["put_price"]),
            put_type=PutType[entry.get("put_type", "EUROPEAN")],
        )
    bond = builder.build()
    settlement = parse_date(inputs["settlement_date"])
    call_flows = bond.cash_flows_to_call(parse_date(inputs["call_flow_date"]))
    return {
        "yield_to_first_workout": bond.yield_to_first_workout(D(inputs["clean_price"]), settlement),
        "call_terminal_amount": call_flows[-1].amount,
        "workout_count": Decimal(len(bond.workout_dates(settlement))),
    }


def _compute_floating_rate_discount_margin(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    frequency = Frequency[inputs["frequency"]]
    frn = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(parse_date(inputs["issue_date"]))
        .with_maturity_date(parse_date(inputs["maturity_date"]))
        .with_index(RateIndex[inputs["index"]])
        .with_quoted_spread(D(inputs["quoted_spread"]))
        .with_current_reference_rate(D(inputs["current_reference_rate"]))
        .with_frequency(frequency)
        .with_rules(_yield_rules(inputs["convention"], frequency))
        .build()
    )
    discount_curve = flat_curve(parse_date(inputs["discount_curve_reference_date"]), D(inputs["discount_curve_zero_rates"][0]["zero_rate"]))
    calculator = DiscountMarginCalculator(discount_curve, discount_curve)
    settlement = parse_date(inputs["settlement_date"])
    dm = D(inputs["discount_margin_decimal"])
    return {
        "market_dirty_price": calculator.price_with_dm(frn, dm, settlement),
        "spread_duration": calculator.spread_duration(frn, dm, settlement),
    }


def _compute_frn_fixing_lookback_coupon(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    frequency = Frequency[inputs["frequency"]]
    store = IndexFixingStore()
    for date, rate in inputs["fixings"].items():
        store.add_fixing(inputs["index"], parse_date(date), D(rate))
    conventions = IndexConventions(
        overnight_compounding=OvernightCompounding[inputs["conventions"]["overnight_compounding"]],
        lookback_days=int(inputs["conventions"]["lookback_days"]),
        shift_type=ObservationShiftType[inputs["conventions"]["shift_type"]],
        lockout_days=int(inputs["conventions"]["lockout_days"]),
    )
    index = BondIndex(
        name=inputs["index"],
        rate_index=RateIndex[inputs["index"]],
        currency=Currency.USD,
        fixing_store=store,
        conventions=conventions,
    )
    frn = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(parse_date(inputs["issue_date"]))
        .with_maturity_date(parse_date(inputs["maturity_date"]))
        .with_index(RateIndex[inputs["index"]])
        .with_index_definition(index)
        .with_quoted_spread(D(inputs["quoted_spread"]))
        .with_current_reference_rate(D(inputs["current_reference_rate"]))
        .with_frequency(frequency)
        .with_currency(Currency.USD)
        .with_notional(D(inputs["notional"]))
        .with_rules(_yield_rules(inputs["convention"], frequency))
        .build()
    )
    projection_curve = linear_zero_curve(
        "corpus.projection",
        parse_date(inputs["settlement_date"]),
        tuple(
            CurvePoint(D(node["tenor_years"]), D(node["zero_rate"]))
            for node in inputs["projection_curve_zero_rates"]
        ),
        extrapolation_policy="hold_last_zero_rate",
    )
    start = parse_date(inputs["period_start"])
    end = parse_date(inputs["period_end"])
    required = frn.required_fixing_dates(start, end, index_conventions=conventions)
    coupon = frn.period_coupon(
        start,
        end,
        fixing_store=store,
        forward_curve=projection_curve,
        index_conventions=conventions,
        as_of=parse_date(inputs["as_of"]),
    )
    return {
        "required_fixings_count": Decimal(len(required)),
        "period_coupon": coupon,
    }


def _compute_curve_conversion(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    built_curve = log_linear_discount_curve(
        "corpus.conversion",
        parse_date(inputs["reference_date"]),
        tuple(
            CurvePoint(D(pillar["tenor_years"]), D(pillar["discount_factor"]))
            for pillar in inputs["discount_curve_pillars"]
        ),
    )
    query_tenor = float(inputs["query_tenor_years"])
    query_df = built_curve.discount_factor_at(query_tenor)
    return {
        "discount_factor_at_query_tenor": _decimal(
            query_df
        ),
        "zero_rate_annual_at_query_tenor": _decimal(
            ValueConverter.df_to_zero(query_df, query_tenor, Compounding[inputs["convert_to"]])
        ),
        "forward_rate_continuous": _decimal(
            built_curve.forward_rate_between(
                float(inputs["forward_start_years"]),
                float(inputs["forward_end_years"]),
            )
        ),
        "converted_rate": _decimal(
            ValueConverter.convert_compounding(
                float(inputs["convert_rate"]),
                Compounding[inputs["convert_from"]],
                Compounding[inputs["convert_to"]],
            )
        ),
    }


def _compute_curve_global_fit_nelson_siegel(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    reference_date = parse_date(inputs["reference_date"])
    true_parameters = tuple(float(value) for value in inputs["true_parameters"])

    def _tenor_label(value: str) -> str:
        years = float(value)
        if years.is_integer():
            return f"{int(years)}Y"
        return f"{int(round(years * 12))}M"

    quotes = tuple(
        SwapQuote(
            instrument_id=_tenor_label(tenor),
            tenor=_tenor_label(tenor),
            rate=_ns_zero(float(tenor), *true_parameters),
            currency="USD",
            as_of=reference_date,
        )
        for tenor in inputs["tenors"]
    )
    curve = YieldCurve.fit(
        quotes,
        spec=CurveSpec(
            name="corpus.nelson-siegel",
            reference_date=reference_date,
            day_count="ACT/365F",
            currency="USD",
            type="nominal",
            extrapolation_policy="error",
        ),
        kernel="nelson_siegel",
        method="global_fit",
        kernel_params={"initial_parameters": true_parameters, "max_t": float(inputs["tenors"][-1])},
    )
    report = curve.calibration_report
    assert isinstance(report, CalibrationReport)
    return {
        "beta0": _decimal(report.kernel_parameters[0]),
        "beta1": _decimal(report.kernel_parameters[1]),
        "beta2": _decimal(report.kernel_parameters[2]),
        "tau": _decimal(report.kernel_parameters[3]),
        "objective_value": _decimal(report.objective_value),
        "zero_rate_4y": _decimal(curve.rate_at(float(inputs["query_tenor_years"]))),
    }


def _portfolio_reference_data(inputs: dict[str, Any]) -> dict[InstrumentId, BondReferenceData]:
    metadata = inputs["reference_data"]
    reference_data: dict[InstrumentId, BondReferenceData] = {}
    for instrument_id, entry in metadata.items():
        parsed_id = InstrumentId(instrument_id)
        reference_data[parsed_id] = BondReferenceData(
            instrument_id=parsed_id,
            bond_type=BondType.FIXED_RATE,
            issuer_type=IssuerType.CORPORATE,
            issue_date=Date.from_ymd(2020, 1, 1),
            maturity_date=Date.from_ymd(2030, 1, 1),
            coupon_rate=Decimal("0.05"),
            frequency=Frequency.SEMI_ANNUAL,
            sector=entry["sector"],
            rating=entry["rating"],
        )
    return reference_data


def _compute_portfolio_weighted_metrics(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    quotes = {
        InstrumentId(entry["instrument_id"]): BondQuoteOutput(
            instrument_id=entry["instrument_id"],
            clean_price=entry["clean_price"],
            dirty_price=entry["dirty_price"],
            yield_to_maturity=entry["yield_to_maturity"],
            modified_duration=entry["modified_duration"],
            convexity=entry["convexity"],
            dv01=entry["dv01"],
        )
        for entry in inputs["quotes"]
    }
    positions = [
        PortfolioPosition(InstrumentId(entry["instrument_id"]), D(entry["notional"]))
        for entry in inputs["positions"]
    ]
    output = PortfolioAnalyzer().analyze(
        PortfolioId(inputs["portfolio_id"]),
        positions,
        quotes,
        reference_data=_portfolio_reference_data(inputs),
    )
    return {
        "weighted_duration": output.weighted_duration,
        "weighted_convexity": output.weighted_convexity,
        "aggregate_dv01": output.aggregate_dv01,
    }


def _portfolio_from_holdings(reference_date: Date, holdings: list[dict[str, Any]]) -> object:
    builder = PortfolioBuilder().with_currency(Currency.USD)
    for holding in holdings:
        frequency = Frequency[holding.get("frequency", "ANNUAL")]
        rating = CreditRating[holding["rating"]]
        sector = Sector[holding["sector"]]
        label = holding["label"]
        bond = FixedBond.new(
            issue_date=reference_date,
            maturity_date=reference_date.add_years(int(holding["years"])),
            coupon_rate=D(holding["coupon_rate"]),
            frequency=frequency,
            currency=Currency.USD,
            rules=_yield_rules(holding.get("convention", "us_corporate"), frequency),
        )
        builder = builder.add_holding(
            Holding(
                id=label,
                instrument=bond,
                quantity=D(holding["quantity"]),
                clean_price=D(holding["clean_price"]),
                label=label,
                classification=Classification(
                    sector=sector,
                    rating=rating,
                    currency=Currency.USD,
                    issuer=f"{label}_issuer",
                ),
                rating_info=RatingInfo(rating=rating),
                sector_info=SectorInfo(sector=sector, issuer=f"{label}_issuer", country="US", region="NA"),
                liquidity_score=D(holding.get("liquidity_score", "0.85")),
            )
        )
    return builder.build()


def _compute_portfolio_benchmark_attribution(case: dict[str, Any]) -> dict[str, Decimal]:
    inputs = case["inputs"]
    reference_date = parse_date(inputs["reference_date"])
    built_curve = linear_zero_curve(
        "corpus.portfolio",
        reference_date,
        tuple(
            CurvePoint(D(node["tenor_years"]), D(node["zero_rate"]))
            for node in inputs["curve_zero_rates"]
        ),
    )
    portfolio = _portfolio_from_holdings(reference_date, inputs["portfolio_holdings"])
    benchmark = _portfolio_from_holdings(reference_date, inputs["benchmark_holdings"])
    assumptions = AttributionInput(
        income_horizon_years=D(inputs["assumptions"]["income_horizon_years"]),
        rate_change_bps=D(inputs["assumptions"]["rate_change_bps"]),
        spread_change_bps=D(inputs["assumptions"]["spread_change_bps"]),
    )
    comparison = benchmark_comparison(portfolio, benchmark, built_curve, reference_date)
    aggregated = aggregated_attribution(
        portfolio,
        curve=built_curve,
        settlement_date=reference_date,
        assumptions=assumptions,
        benchmark=benchmark,
    )
    return {
        "active_duration": comparison.active_duration,
        "active_z_spread": comparison.active_z_spread,
        "active_total_return": aggregated.active_total_return or Decimal(0),
        "income_return": aggregated.income_return,
        "rate_return": aggregated.rate_return,
        "spread_return": aggregated.spread_return,
    }


CASE_COMPUTERS = {
    "fixed_rate_bullet": _compute_fixed_rate_bullet,
    "zero_coupon": _compute_zero_coupon,
    "accrued_interest_ex_dividend": _compute_accrued_interest_ex_dividend,
    "callable_oas_effective_duration": _compute_callable_oas,
    "callable_workout_behavior": _compute_callable_workout_behavior,
    "floating_rate_note_discount_margin": _compute_floating_rate_discount_margin,
    "frn_fixing_lookback_coupon": _compute_frn_fixing_lookback_coupon,
    "curve_conversion_interpolation": _compute_curve_conversion,
    "curve_global_fit_nelson_siegel": _compute_curve_global_fit_nelson_siegel,
    "portfolio_weighted_metrics": _compute_portfolio_weighted_metrics,
    "portfolio_benchmark_attribution": _compute_portfolio_benchmark_attribution,
}


def test_validation_corpus_is_pinned_to_reference_revision() -> None:
    corpus = _load_corpus()
    source = corpus["source"]
    assert source["repository"] == "https://github.com/sujitn/convex"
    assert source["branch"] == "main"
    assert re.fullmatch(r"[0-9a-f]{40}", source["pinned_commit"])
    assert source["pinned_commit"] == "6ba6b323eed2b1a24e131d1e170afb09f062a773"
    assert [case["id"] for case in corpus["cases"]] == EXPECTED_CASE_IDS


def test_validation_corpus_explicitly_marks_accepted_divergences() -> None:
    cases = _cases_by_id()
    divergence_reasons = {
        case_id: cases[case_id].get("accepted_divergence_reason")
        for case_id in EXPECTED_CASE_IDS
        if cases[case_id].get("accepted_divergence_reason")
    }
    assert divergence_reasons == {
        "callable_oas_effective_duration": cases["callable_oas_effective_duration"]["accepted_divergence_reason"],
        "floating_rate_note_discount_margin": cases["floating_rate_note_discount_margin"]["accepted_divergence_reason"],
    }


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_validation_corpus(case_id: str) -> None:
    case = _cases_by_id()[case_id]
    actual = CASE_COMPUTERS[case_id](case)

    for metric, expected in case["expected"].items():
        assert metric in actual, f"Missing computed metric {metric!r} for case {case_id!r}"
        assert_decimal_close(_decimal(actual[metric]), D(expected), D(case["tolerances"][metric]))
