from __future__ import annotations

import math

import numpy as np
import pytest

from fuggers_py.math.extrapolation import FlatExtrapolator, LinearExtrapolator, SmithWilson


def test_flat_extrapolator_constant() -> None:
    ex = FlatExtrapolator(level=1.23)
    assert ex.extrapolate(-10.0) == pytest.approx(1.23)
    assert ex.extrapolate(10.0) == pytest.approx(1.23)
    assert ex.derivative(0.0) == pytest.approx(0.0)


def test_linear_extrapolator_slope() -> None:
    ex = LinearExtrapolator(x0=1.0, y0=2.0, slope=3.0)
    assert ex.extrapolate(2.0) == pytest.approx(5.0)
    assert ex.derivative(2.0) == pytest.approx(3.0)


def test_smith_wilson_recovers_pillars_and_converges_to_ufr() -> None:
    maturities = np.array([1.0, 2.0, 3.0, 5.0])
    true_ufr = 0.03
    zeros = np.array([0.015, 0.0175, 0.02, 0.022])
    dfs = np.exp(-zeros * maturities)
    sw = SmithWilson(maturities, dfs, ufr=true_ufr, alpha=0.1)

    for t, df in zip(maturities, dfs, strict=True):
        assert sw.discount_factor(float(t)) == pytest.approx(float(df), rel=0, abs=1e-10)

    t_long = 60.0
    df_long = sw.discount_factor(t_long)
    z_long = -math.log(df_long) / t_long
    assert z_long == pytest.approx(true_ufr, abs=5e-3)

