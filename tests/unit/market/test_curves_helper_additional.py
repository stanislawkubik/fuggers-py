from __future__ import annotations

import pytest

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Frequency, SpreadType
from fuggers_py.market.curves.conversion import ValueConverter
from fuggers_py.market.curves.errors import InvalidCurveInput
from fuggers_py.market.curves.value_type import ValueType


def test_value_type_validates_supported_field_combinations() -> None:
    with pytest.raises(InvalidCurveInput, match="carries no fields"):
        ValueType(kind=ValueType.discount_factor().kind, tenor=1.0)

    with pytest.raises(InvalidCurveInput, match="requires compounding and day_count"):
        ValueType(kind=ValueType.zero_rate(Compounding.ANNUAL).kind)

    with pytest.raises(InvalidCurveInput, match="requires tenor and compounding"):
        ValueType(kind=ValueType.forward_rate(0.5).kind)

    with pytest.raises(InvalidCurveInput, match="requires spread_type and recovery"):
        ValueType(kind=ValueType.credit_spread(SpreadType.CREDIT).kind)

    with pytest.raises(InvalidCurveInput, match="requires frequency and day_count"):
        ValueType(kind=ValueType.par_swap_rate(Frequency.ANNUAL, DayCountConvention.ACT_365_FIXED).kind)


def test_value_type_short_names_and_string_forms_cover_remaining_variants() -> None:
    assert ValueType.continuous_zero().short_name() == "Zero"
    assert ValueType.forward_6m().short_name() == "Fwd"
    assert str(ValueType.credit_spread(SpreadType.CREDIT)) == "CreditSpread(Credit, 0.4)"
    assert str(ValueType.par_swap_rate(Frequency.ANNUAL, DayCountConvention.ACT_365_FIXED)) == "ParSwapRate(Annual, ACT/365F)"


def test_value_converter_handles_zero_tenor_and_boundary_cases() -> None:
    assert ValueConverter.df_to_zero(0.95, 0.0, Compounding.CONTINUOUS) == 0.0
    assert ValueConverter.zero_to_df(0.05, 0.0, Compounding.CONTINUOUS) == 1.0
    assert ValueConverter.forward_rate_from_zeros(0.03, 0.04, 2.0, 2.0) == 0.04
    assert ValueConverter.forward_rate_from_dfs(0.99, 0.97, 1.0, 2.0, Compounding.SIMPLE) == pytest.approx(
        (0.99 / 0.97) - 1.0,
        abs=1e-12,
    )


def test_value_converter_rejects_negative_tenors_and_clamps_tiny_negative_hazards() -> None:
    with pytest.raises(InvalidCurveInput, match="Tenor must be non-negative"):
        ValueConverter.df_to_zero(0.95, -1.0, Compounding.CONTINUOUS)

    with pytest.raises(InvalidCurveInput, match="Tenor must be non-negative"):
        ValueConverter.hazard_to_survival(0.02, -1.0)

    assert ValueConverter.survival_to_hazard(0.95, 1e-13) == 0.0
