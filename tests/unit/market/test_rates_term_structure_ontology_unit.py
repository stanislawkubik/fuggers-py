from __future__ import annotations

import math

import pytest

from fuggers_py.core.types import Currency, Date
from fuggers_py.market.curves import CurveSpec, CurveType, ExtrapolationPolicy, RateSpace, RatesTermStructure
from fuggers_py.market.curves.errors import InvalidCurveInput, TenorOutOfBounds


class _FlatZeroCurve(RatesTermStructure):
    def __init__(
        self,
        spec: CurveSpec,
        *,
        rate: float = 0.03,
        max_t: float = 5.0,
    ) -> None:
        super().__init__(spec)
        self._rate = rate
        self._max_t = max_t

    @property
    def rate_space(self) -> RateSpace:
        return RateSpace.ZERO

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        return self._rate


def test_curve_spec_normalizes_native_fields() -> None:
    spec = CurveSpec(
        name="  USD Nominal  ",
        reference_date=Date.parse("2026-04-09"),
        day_count=" act_365_fixed ",
        currency="usd",
        type=CurveType.NOMINAL,
        reference=" USD-SOFR ",
    )

    assert spec.name == "USD Nominal"
    assert spec.day_count == "ACT_365_FIXED"
    assert spec.currency is Currency.USD
    assert spec.reference == "USD-SOFR"


def test_validate_rate_returns_value_on_domain() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        )
    )

    assert curve.reference_date == Date.parse("2026-04-09")
    assert curve.rate_space is RateSpace.ZERO
    assert curve.validate_rate(2.0) == pytest.approx(0.03)


def test_validate_rate_rejects_negative_t() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        )
    )

    with pytest.raises(InvalidCurveInput, match="t must be >= 0"):
        curve.validate_rate(-0.25)


def test_validate_rate_rejects_t_beyond_domain_when_extrapolation_forbidden() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
            extrapolation_policy=ExtrapolationPolicy.ERROR,
        ),
        max_t=3.0,
    )

    with pytest.raises(TenorOutOfBounds):
        curve.validate_rate(4.0)


def test_validate_rate_allows_t_beyond_domain_when_policy_is_not_error() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
            extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_NATIVE_RATE,
        ),
        max_t=3.0,
    )

    assert curve.validate_rate(4.0) == pytest.approx(0.03)


def test_validate_rate_rejects_non_finite_values() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        ),
        rate=math.inf,
    )

    with pytest.raises(InvalidCurveInput, match="must be finite"):
        curve.validate_rate(1.0)
