from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core import Compounding, Currency, Date
from fuggers_py.market.curves import (
    CreditCurve,
    CurrencyPair,
    CurveBuilder,
    CurveFamily,
    CurveTransform,
    DelegatedCurve,
    DerivedCurve,
    ScenarioBump,
    SegmentedCurve,
    SegmentBuilder,
    STANDARD_KEY_TENORS,
    key_rate_profile,
)
from fuggers_py.market.curves import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py.market.curves.value_type import ValueType
from fuggers_py.market.curves.wrappers import RateCurve


def test_curve_builder_builds_segmented_discount_curve() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = (
        CurveBuilder.discount(ref)
        .add_segment(
            SegmentBuilder(0.0, 5.0).with_pillars(
                [0.0, 2.0, 5.0],
                [1.0, 0.97, 0.90],
                value_type=ValueType.discount_factor(),
                interpolation_method=InterpolationMethod.LOG_LINEAR,
            )
        )
        .add_segment(
            SegmentBuilder(5.0, 30.0).with_pillars(
                [5.0, 10.0, 30.0],
                [0.90, 0.80, 0.40],
                value_type=ValueType.discount_factor(),
                interpolation_method=InterpolationMethod.LOG_LINEAR,
                extrapolation_method=ExtrapolationMethod.FLAT,
            )
        )
        .build()
    )

    assert isinstance(curve.curve, SegmentedCurve)
    assert float(curve.discount_factor(ref.add_days(365 * 7))) < 1.0


def test_delegated_curve_falls_back_out_of_range() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    primary = DiscreteCurve(
        ref,
        [0.0, 2.0],
        [1.0, 0.95],
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LOG_LINEAR,
    )
    fallback = DiscreteCurve(
        ref,
        [0.0, 10.0],
        [1.0, 0.70],
        value_type=ValueType.discount_factor(),
        interpolation_method=InterpolationMethod.LOG_LINEAR,
    )
    delegated = DelegatedCurve(primary=primary, fallback=fallback)

    assert delegated.value_at(1.0) == pytest.approx(primary.value_at(1.0))
    assert delegated.value_at(5.0) == pytest.approx(fallback.value_at(5.0))


def test_derived_curve_applies_parallel_shift() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base = RateCurve(
        DiscreteCurve(
            ref,
            [1.0, 30.0],
            [0.03, 0.03],
            value_type=ValueType.zero_rate(Compounding.CONTINUOUS),
            interpolation_method=InterpolationMethod.LINEAR,
        )
    )
    shifted = DerivedCurve.from_curve(base, CurveTransform.parallel_shift(Decimal("0.0025")))
    date = ref.add_days(365 * 10)
    assert float(shifted.zero_rate(date).value()) == pytest.approx(0.0325, abs=1e-12)


def test_credit_curve_converts_hazard_rates_to_survival_probabilities() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    credit_curve = CurveBuilder.credit(ref, family=CurveFamily.HAZARD_RATE).add_pillar(1.0, 0.02).add_pillar(5.0, 0.02).build()
    assert isinstance(credit_curve, CreditCurve)
    survival = credit_curve.survival_probability(ref.add_days(365 * 5))
    assert Decimal("0") < survival < Decimal("1")


def test_curve_compatibility_exports() -> None:
    pair = CurrencyPair(base=Currency.USD, quote=Currency.EUR)
    assert str(pair) == "USD/EUR"
    assert pair.inverse().base is Currency.EUR


def test_key_rate_profile_and_scenario_aliases() -> None:
    profile = key_rate_profile(Tenor.parse("5Y"))
    assert profile[Tenor.parse("5Y")] == pytest.approx(1e-4)
    scenario = ScenarioBump([Tenor.parse("1Y"), Tenor.parse("30Y")], [0.001, 0.002])
    assert scenario.bump_at(Tenor.parse("10Y")) > 0
