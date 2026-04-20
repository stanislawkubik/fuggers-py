from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Tenor
from fuggers_py._core.daycounts import DayCountConvention
from fuggers_py._core.types import Compounding, Date, Frequency
from fuggers_py._curves_impl import ZeroCurveBuilder
from fuggers_py._curves_impl.calibration import Deposit, InstrumentSet, PiecewiseBootstrapper, Swap
from fuggers_py._curves_impl.value_type import ValueTypeKind


def test_piecewise_bootstrap_from_synthetic_quotes() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    flat_rate = 0.04
    source_curve = (
        ZeroCurveBuilder(reference_date=ref, compounding=Compounding.SEMI_ANNUAL)
        .add_rate(ref.add_days(365), Decimal(str(flat_rate)))
        .add_rate(ref.add_days(365 * 10), Decimal(str(flat_rate)))
        .build()
    )

    deposit = Deposit(reference_date=ref, tenor=Tenor.parse("6M"), quote=Decimal("0"))
    swap_1y = Swap(reference_date=ref, tenor=Tenor.parse("1Y"), quote=Decimal("0"), fixed_frequency=Frequency.SEMI_ANNUAL)
    swap_2y = Swap(reference_date=ref, tenor=Tenor.parse("2Y"), quote=Decimal("0"), fixed_frequency=Frequency.SEMI_ANNUAL)
    swap_3y = Swap(reference_date=ref, tenor=Tenor.parse("3Y"), quote=Decimal("0"), fixed_frequency=Frequency.SEMI_ANNUAL)

    instruments = [
        Deposit(reference_date=ref, tenor=Tenor.parse("6M"), quote=deposit.par_rate(source_curve)),
        Swap(reference_date=ref, tenor=Tenor.parse("1Y"), quote=swap_1y.par_rate(source_curve), fixed_frequency=Frequency.SEMI_ANNUAL),
        Swap(reference_date=ref, tenor=Tenor.parse("2Y"), quote=swap_2y.par_rate(source_curve), fixed_frequency=Frequency.SEMI_ANNUAL),
        Swap(reference_date=ref, tenor=Tenor.parse("3Y"), quote=swap_3y.par_rate(source_curve), fixed_frequency=Frequency.SEMI_ANNUAL),
    ]

    instrument_set = InstrumentSet(instruments)
    bootstrapper = PiecewiseBootstrapper(
        reference_date=ref,
        instruments=instrument_set,
        value_type_kind=ValueTypeKind.DISCOUNT_FACTOR,
        curve_day_count=DayCountConvention.ACT_365_FIXED,
    )

    result = bootstrapper.bootstrap()
    curve = result.curve

    for inst in instruments:
        assert float(inst.par_rate(curve)) == pytest.approx(float(inst.quote), abs=1e-8)

    dfs = [float(curve.discount_factor(inst.maturity_date())) for inst in instruments]
    assert all(df > 0 for df in dfs)
    assert all(dfs[i] >= dfs[i + 1] for i in range(len(dfs) - 1))

    for inst in instruments:
        base_zero = source_curve.zero_rate(inst.maturity_date()).value()
        boot_zero = curve.zero_rate(inst.maturity_date()).value()
        assert float(boot_zero) == pytest.approx(float(base_zero), abs=5e-6)
