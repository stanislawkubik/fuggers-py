from __future__ import annotations

import math
from decimal import Decimal

import pytest

from fuggers_py.core import Compounding, Date, SpreadType
from fuggers_py.market.curves.conversion import ValueConverter
from fuggers_py.market.curves.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py.market.curves.errors import InvalidCurveInput
from fuggers_py.market.curves.value_type import ValueType
from fuggers_py.market.curves.wrappers import CreditCurve


@pytest.mark.parametrize(
    "compounding",
    [
        Compounding.CONTINUOUS,
        Compounding.SIMPLE,
        Compounding.ANNUAL,
        Compounding.SEMI_ANNUAL,
        Compounding.QUARTERLY,
        Compounding.MONTHLY,
        Compounding.DAILY,
    ],
)
def test_value_converter_zero_discount_round_trip_is_stable(compounding: Compounding) -> None:
    zero_rate = 0.0375
    tenor = 2.5

    discount_factor = ValueConverter.zero_to_df(zero_rate, tenor, compounding)
    recovered = ValueConverter.df_to_zero(discount_factor, tenor, compounding)

    assert recovered == pytest.approx(zero_rate, abs=1e-12)


def test_value_converter_risky_discount_factor_is_monotone_in_survival_and_recovery() -> None:
    base = ValueConverter.risky_discount_factor(0.97, 0.85, 0.40)
    better_survival = ValueConverter.risky_discount_factor(0.97, 0.90, 0.40)
    better_recovery = ValueConverter.risky_discount_factor(0.97, 0.85, 0.60)

    assert better_survival > base
    assert better_recovery > base


def test_credit_curve_flat_hazard_inputs_are_self_consistent() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    inner = DiscreteCurve(
        reference_date,
        tenors=[1.0, 5.0],
        values=[0.02, 0.02],
        value_type=ValueType.hazard_rate(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    credit_curve = CreditCurve(inner, recovery_rate=Decimal("0.4"))

    assert credit_curve.hazard_rate_at_tenor(3.0) == Decimal("0.02")
    assert float(credit_curve.survival_probability_at_tenor(3.0)) == pytest.approx(math.exp(-0.06), abs=1e-12)
    assert credit_curve.credit_spread_at_tenor(3.0) == Decimal("0.012")
    assert credit_curve.survival_probability(reference_date.add_days(365 * 3)) == credit_curve.survival_probability_at_tenor(3.0)


def test_credit_curve_survival_and_spread_inputs_convert_back_to_the_same_hazard() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    hazard = 0.03
    survival_inner = DiscreteCurve(
        reference_date,
        tenors=[1.0, 3.0],
        values=[
            ValueConverter.hazard_to_survival(hazard, 1.0),
            ValueConverter.hazard_to_survival(hazard, 3.0),
        ],
        value_type=ValueType.survival_probability(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    spread_inner = DiscreteCurve(
        reference_date,
        tenors=[1.0, 3.0],
        values=[0.018, 0.018],
        value_type=ValueType.credit_spread(SpreadType.CREDIT),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )

    survival_curve = CreditCurve(survival_inner, recovery_rate=Decimal("0.4"))
    spread_curve = CreditCurve(spread_inner, recovery_rate=Decimal("0.4"))

    assert float(survival_curve.hazard_rate_at_tenor(3.0)) == pytest.approx(hazard, abs=1e-12)
    assert float(spread_curve.hazard_rate_at_tenor(3.0)) == pytest.approx(hazard, abs=1e-12)
    assert survival_curve.survival_probability_at_tenor(0.0) == Decimal(1)
    assert spread_curve.hazard_rate_at_tenor(0.0) == Decimal(0)


def test_credit_curve_rejects_invalid_survival_outputs() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    inner = DiscreteCurve(
        reference_date,
        tenors=[1.0, 5.0],
        values=[1.1, 1.1],
        value_type=ValueType.survival_probability(),
        interpolation_method=InterpolationMethod.LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )

    with pytest.raises(InvalidCurveInput, match="values in \\[0, 1\\]"):
        CreditCurve(inner).survival_probability_at_tenor(2.0)
