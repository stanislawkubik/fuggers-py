from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core import Currency, Date
from fuggers_py.pricers.credit import CdsPricer
from fuggers_py.products.credit import CreditDefaultSwap
from fuggers_py.market.curves import DelegatedCurve, DelegationFallback, DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py.market.curves.term_structure import TermStructure
from fuggers_py.market.curves.value_type import ValueType
from fuggers_py.calc import AnalyticsCurves
from fuggers_py.pricers.rates._curve_resolver import resolve_discount_curve, resolve_projection_curve

from tests.helpers._rates_helpers import flat_curve


class _BrokenDiscountEnvironment:
    def discount_curve(self, currency: Currency):
        raise RuntimeError(f"broken discount environment for {currency.code()}")


class _BrokenProjectionEnvironment:
    def projection_curve(self, index):
        raise RuntimeError(f"broken projection environment for {index}")


class _ExplodingInterpolator:
    def interpolate(self, x: float) -> float:
        raise RuntimeError(f"broken interpolator at {x}")

    def derivative(self, x: float) -> float:
        return 0.0


class _ExplodingPrimaryCurve(TermStructure):
    def __init__(self, reference_date: Date) -> None:
        self._reference_date = reference_date

    def reference_date(self) -> Date:
        return self._reference_date

    def value_at(self, t: float) -> float:
        raise RuntimeError(f"primary curve failure at {t}")

    def tenor_bounds(self) -> tuple[float, float]:
        return 0.0, 5.0

    def value_type(self) -> ValueType:
        return ValueType.discount_factor()

    def max_date(self) -> Date:
        return self._reference_date.add_years(5)


def test_resolve_discount_curve_propagates_environment_failures() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curves = AnalyticsCurves(
        discount_curve=flat_curve(ref, "0.03"),
        multicurve_environment=_BrokenDiscountEnvironment(),
    )

    with pytest.raises(RuntimeError, match="broken discount environment"):
        resolve_discount_curve(curves, Currency.USD)


def test_resolve_projection_curve_propagates_environment_failures() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curves = AnalyticsCurves(
        discount_curve=flat_curve(ref, "0.03"),
        forward_curve=flat_curve(ref, "0.031"),
        multicurve_environment=_BrokenProjectionEnvironment(),
    )

    with pytest.raises(RuntimeError, match="broken projection environment"):
        resolve_projection_curve(
            curves,
            currency=Currency.USD,
            index_name="SOFR",
            index_tenor=Tenor.parse("3M"),
        )


def test_cds_pricer_propagates_discount_environment_failures() -> None:
    ref = Date.from_ymd(2026, 1, 2)
    credit_curve = DiscreteCurve(
        ref,
        tenors=[1e-8, 10.0],
        values=[1.0, 0.8],
        value_type=ValueType.survival_probability(),
        interpolation_method=InterpolationMethod.LOG_LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    curves = AnalyticsCurves(
        discount_curve=flat_curve(ref, "0.00"),
        credit_curve=credit_curve,
        multicurve_environment=_BrokenDiscountEnvironment(),
    )
    cds = CreditDefaultSwap(
        effective_date=ref,
        maturity_date=ref.add_years(5),
        running_spread=Decimal("0.012"),
        notional=Decimal("1000000"),
    )

    with pytest.raises(RuntimeError, match="broken discount environment"):
        CdsPricer().price(cds, curves)


def test_discrete_curve_propagates_interpolator_failures_in_range() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = DiscreteCurve(
        ref,
        tenors=[1.0, 2.0],
        values=[0.01, 0.02],
        value_type=ValueType.continuous_zero(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    object.__setattr__(curve, "_interpolator", _ExplodingInterpolator())

    with pytest.raises(RuntimeError, match="broken interpolator"):
        curve.value_at(1.5)


def test_delegated_curve_propagates_primary_failures_for_missing_value_mode() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    fallback = DiscreteCurve(
        ref,
        tenors=[0.0, 5.0],
        values=[1.0, 0.9],
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    delegated = DelegatedCurve(
        primary=_ExplodingPrimaryCurve(ref),
        fallback=fallback,
        fallback_mode=DelegationFallback.MISSING_VALUE,
    )

    with pytest.raises(RuntimeError, match="primary curve failure"):
        delegated.value_at(1.0)
