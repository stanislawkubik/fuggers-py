from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core.types import Compounding, Date
from fuggers_py.market.curves import ZeroCurveBuilder
from fuggers_py.market.curves.bumping import (
    KeyRateBump,
    ParallelBump,
    flattener_50bp,
    parallel_down_50bp,
    parallel_up_50bp,
    steepener_50bp,
)


def _base_curve() -> tuple[Date, object]:
    ref = Date.from_ymd(2024, 1, 1)
    curve = (
        ZeroCurveBuilder(reference_date=ref, compounding=Compounding.CONTINUOUS)
        .add_rate(ref.add_days(365), Decimal("0.03"))
        .add_rate(ref.add_days(365 * 30), Decimal("0.03"))
        .build()
    )
    return ref, curve


def test_parallel_bump_shifts_zero_rates_and_discount_factors() -> None:
    ref, curve = _base_curve()
    date = ref.add_days(365 * 5)

    base_zero = curve.zero_rate(date).value()
    base_df = curve.discount_factor(date)

    bumped_up = ParallelBump(0.005).apply(curve)
    bumped_down = ParallelBump(-0.005).apply(curve)

    up_zero = bumped_up.zero_rate(date).value()
    down_zero = bumped_down.zero_rate(date).value()

    assert float(up_zero) == pytest.approx(float(base_zero) + 0.005, abs=1e-12)
    assert float(down_zero) == pytest.approx(float(base_zero) - 0.005, abs=1e-12)

    assert float(bumped_up.discount_factor(date)) < float(base_df)
    assert float(bumped_down.discount_factor(date)) > float(base_df)


def test_key_rate_bump_is_localized() -> None:
    ref, curve = _base_curve()
    grid = [Tenor.parse("1Y"), Tenor.parse("2Y"), Tenor.parse("5Y"), Tenor.parse("10Y")]
    bump = KeyRateBump(tenors=grid, key_tenor=Tenor.parse("5Y"), bump=0.005)
    bumped_curve = bump.apply(curve)

    date_2y = ref.add_days(365 * 2)
    date_5y = ref.add_days(365 * 5)
    date_7y = ref.add_days(365 * 7)
    date_10y = ref.add_days(365 * 10)

    base_2y = curve.zero_rate(date_2y).value()
    base_5y = curve.zero_rate(date_5y).value()
    base_7y = curve.zero_rate(date_7y).value()
    base_10y = curve.zero_rate(date_10y).value()

    bumped_2y = bumped_curve.zero_rate(date_2y).value()
    bumped_5y = bumped_curve.zero_rate(date_5y).value()
    bumped_7y = bumped_curve.zero_rate(date_7y).value()
    bumped_10y = bumped_curve.zero_rate(date_10y).value()

    assert float(bumped_2y) == pytest.approx(float(base_2y), abs=1e-12)
    assert float(bumped_10y) == pytest.approx(float(base_10y), abs=1e-12)
    assert float(bumped_5y) == pytest.approx(float(base_5y) + 0.005, abs=1e-12)
    assert float(bumped_7y) > float(base_7y)
    assert float(bumped_7y) < float(base_7y) + 0.005


def test_scenario_presets_move_short_and_long_ends_oppositely() -> None:
    ref, curve = _base_curve()
    short_date = ref.add_days(365 * 2)
    long_date = ref.add_days(365 * 30)

    base_short = curve.zero_rate(short_date).value()
    base_long = curve.zero_rate(long_date).value()

    steep_curve = steepener_50bp().apply(curve)
    flat_curve = flattener_50bp().apply(curve)

    assert float(steep_curve.zero_rate(short_date).value()) < float(base_short)
    assert float(steep_curve.zero_rate(long_date).value()) > float(base_long)

    assert float(flat_curve.zero_rate(short_date).value()) > float(base_short)
    assert float(flat_curve.zero_rate(long_date).value()) < float(base_long)


def test_parallel_scenario_helpers() -> None:
    ref, curve = _base_curve()
    date = ref.add_days(365 * 5)
    base_zero = curve.zero_rate(date).value()

    up_curve = parallel_up_50bp().apply(curve)
    down_curve = parallel_down_50bp().apply(curve)

    assert float(up_curve.zero_rate(date).value()) == pytest.approx(float(base_zero) + 0.005, abs=1e-12)
    assert float(down_curve.zero_rate(date).value()) == pytest.approx(float(base_zero) - 0.005, abs=1e-12)
