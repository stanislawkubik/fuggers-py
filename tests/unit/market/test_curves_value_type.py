from __future__ import annotations

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Frequency, SpreadType
from fuggers_py.market.curves.value_type import ValueType, ValueTypeKind


def test_value_type_constructors_and_predicates() -> None:
    df = ValueType.discount_factor()
    assert df.kind is ValueTypeKind.DISCOUNT_FACTOR
    assert str(ValueTypeKind.DISCOUNT_FACTOR) == "ValueTypeKind.DISCOUNT_FACTOR"
    assert df.can_convert_to_discount_factor() is True
    assert df.is_rate_type() is False
    assert df.is_probability_type() is True

    zr = ValueType.zero_rate(Compounding.CONTINUOUS)
    assert zr.kind is ValueTypeKind.ZERO_RATE
    assert zr.compounding is Compounding.CONTINUOUS
    assert zr.day_count is DayCountConvention.ACT_365_FIXED
    assert zr.can_convert_to_discount_factor() is True
    assert zr.is_rate_type() is True
    assert zr.is_probability_type() is False

    fwd3m = ValueType.forward_3m(Compounding.ANNUAL)
    assert fwd3m.kind is ValueTypeKind.FORWARD_RATE
    assert fwd3m.tenor == 0.25
    assert fwd3m.compounding is Compounding.ANNUAL

    inst = ValueType.instantaneous_forward()
    assert inst.kind is ValueTypeKind.INSTANTANEOUS_FORWARD

    sp = ValueType.survival_probability()
    assert sp.can_convert_to_discount_factor() is True
    assert sp.is_credit_type() is True

    hz = ValueType.hazard_rate()
    assert hz.is_credit_type() is True
    assert hz.is_rate_type() is True

    cs = ValueType.credit_spread(SpreadType.Z_SPREAD)
    assert cs.is_credit_type() is True
    assert cs.recovery == 0.40

    fx = ValueType.fx_forward_points()
    assert fx.kind is ValueTypeKind.FX_FORWARD_POINTS

    ps = ValueType.par_swap_rate(Frequency.SEMI_ANNUAL, DayCountConvention.ACT_365_FIXED)
    assert ps.kind is ValueTypeKind.PAR_SWAP_RATE
