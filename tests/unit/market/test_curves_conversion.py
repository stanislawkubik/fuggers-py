from __future__ import annotations

import math

import pytest

from fuggers_py._core.types import Compounding
from fuggers_py._curves_impl.conversion import ValueConverter


def test_df_zero_round_trip_continuous() -> None:
    r = 0.05
    t = 1.0
    df = math.exp(-r * t)
    z = ValueConverter.df_to_zero(df, t, Compounding.CONTINUOUS)
    assert z == pytest.approx(r, abs=1e-12)
    df_back = ValueConverter.zero_to_df(z, t, Compounding.CONTINUOUS)
    assert df_back == pytest.approx(df, abs=1e-12)


def test_convert_compounding_preserves_one_year_factor() -> None:
    r_cont = 0.03
    r_annual = ValueConverter.convert_compounding(r_cont, Compounding.CONTINUOUS, Compounding.ANNUAL)
    r_cont_back = ValueConverter.convert_compounding(r_annual, Compounding.ANNUAL, Compounding.CONTINUOUS)
    assert r_cont_back == pytest.approx(r_cont, abs=1e-12)


def test_forward_rate_from_discount_factors_constant_rate() -> None:
    r = 0.05
    t1 = 1.0
    t2 = 2.0
    df1 = math.exp(-r * t1)
    df2 = math.exp(-r * t2)
    f = ValueConverter.forward_rate_from_dfs(df1, df2, t1, t2, Compounding.CONTINUOUS)
    assert f == pytest.approx(r, abs=1e-12)


def test_survival_and_hazard_conversions() -> None:
    t = 2.0
    hz = 0.01
    sp = ValueConverter.hazard_to_survival(hz, t)
    assert sp == pytest.approx(math.exp(-hz * t), abs=1e-12)
    hz_imp = ValueConverter.implied_hazard_rate(sp, t)
    assert hz_imp == pytest.approx(hz, abs=1e-12)

