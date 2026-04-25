from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from fuggers_py._core import Currency, Date, Frequency, InstrumentId, YieldCalculationRules
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py.bonds.reference_data import BondReferenceData
from fuggers_py.bonds.types import BondType, IssuerType


REFERENCE_DATE = Date.from_ymd(2026, 1, 15)
UNIVERSE = (
    ("UST2Y", 2, Decimal("0.0200"), Decimal("-1.2"), Decimal("400000000"), Decimal("0.80"), False),
    ("UST3Y", 3, Decimal("0.0225"), Decimal("-0.8"), Decimal("500000000"), Decimal("0.90"), False),
    ("UST4Y", 4, Decimal("0.0250"), Decimal("-0.4"), Decimal("700000000"), Decimal("1.00"), True),
    ("UST5Y", 5, Decimal("0.0275"), Decimal("0.0"), Decimal("900000000"), Decimal("1.10"), True),
    ("UST6Y", 6, Decimal("0.0300"), Decimal("0.4"), Decimal("1100000000"), Decimal("1.15"), True),
    ("UST8Y", 8, Decimal("0.0350"), Decimal("0.8"), Decimal("800000000"), Decimal("1.00"), True),
    ("UST10Y", 10, Decimal("0.0400"), Decimal("1.2"), Decimal("600000000"), Decimal("0.85"), False),
)


@dataclass(frozen=True, slots=True)
class _CurveModel:
    name: str


class _FittedBondResult:
    def __init__(self, points: tuple[Mapping[str, object], ...]) -> None:
        self._points = points
        self._by_id = {point["instrument_id"].as_str(): point for point in points}

    @property
    def bonds(self) -> tuple[Mapping[str, object], ...]:
        return self._points

    def get_bond(self, instrument_id: object) -> Mapping[str, object]:
        return self._by_id[InstrumentId.parse(instrument_id).as_str()]

    def date(self) -> Date:
        return REFERENCE_DATE


def exponential_model() -> _CurveModel:
    return _CurveModel("exponential")


def _bond(
    instrument_id: InstrumentId,
    *,
    maturity_years: int,
    coupon_rate: Decimal,
):
    return (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2021, 1, 15))
        .with_maturity_date(REFERENCE_DATE.add_years(maturity_years))
        .with_coupon_rate(coupon_rate)
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_instrument_id(instrument_id)
        .with_rules(YieldCalculationRules.us_treasury())
        .build()
    )


def _reference_data(
    instrument_id: InstrumentId,
    *,
    maturity_years: int,
    coupon_rate: Decimal,
    amount_outstanding: Decimal,
    liquidity_score: Decimal,
    benchmark_flag: bool,
) -> BondReferenceData:
    return BondReferenceData(
        instrument_id=instrument_id,
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


def fit_result(
    *,
    curve_model: object | None = None,
    regression_coefficient: Decimal = Decimal("0"),
    mispricings: dict[str, Decimal] | None = None,
    **_: object,
) -> _FittedBondResult:
    del curve_model, regression_coefficient
    resolved_mispricings = mispricings or {}
    points: list[Mapping[str, object]] = []
    for (
        instrument_id_text,
        maturity_years,
        coupon_rate,
        _exposure_value,
        amount_outstanding,
        liquidity_score,
        benchmark_flag,
    ) in UNIVERSE:
        instrument_id = InstrumentId(instrument_id_text)
        price_residual = resolved_mispricings.get(instrument_id_text, Decimal(0))
        bp_residual = -price_residual * Decimal("2")
        points.append(
            {
                "instrument_id": instrument_id,
                "bond": _bond(instrument_id, maturity_years=maturity_years, coupon_rate=coupon_rate),
                "reference_data": _reference_data(
                    instrument_id,
                    maturity_years=maturity_years,
                    coupon_rate=coupon_rate,
                    amount_outstanding=amount_outstanding,
                    liquidity_score=liquidity_score,
                    benchmark_flag=benchmark_flag,
                ),
                "maturity_years": Decimal(maturity_years),
                "fitted_yield": coupon_rate,
                "price_residual": price_residual,
                "bp_residual": bp_residual,
            }
        )
    return _FittedBondResult(tuple(points))
