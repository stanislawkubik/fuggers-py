from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Tenor
from fuggers_py._core.types import Compounding, Date, Frequency
from fuggers_py._curves_impl import ZeroCurveBuilder
from fuggers_py._curves_impl.calibration import Deposit, Fra, InstrumentSet, Ois, Swap
from fuggers_py._curves_impl.errors import InvalidCurveInput


def _flat_curve(rate: float, *, compounding: Compounding) -> tuple[Date, object]:
    ref = Date.from_ymd(2024, 1, 1)
    curve = (
        ZeroCurveBuilder(reference_date=ref, compounding=compounding)
        .add_rate(ref.add_days(365), Decimal(str(rate)))
        .add_rate(ref.add_days(365 * 10), Decimal(str(rate)))
        .build()
    )
    return ref, curve


def test_deposit_reprices_on_flat_curve() -> None:
    ref, curve = _flat_curve(0.05, compounding=Compounding.SIMPLE)
    dep = Deposit(reference_date=ref, tenor=Tenor.parse("6M"), quote=Decimal("0.05"))
    assert float(dep.par_rate(curve)) == pytest.approx(0.05, abs=1e-10)


def test_fra_implied_forward_matches_curve_forward() -> None:
    ref, curve = _flat_curve(0.04, compounding=Compounding.CONTINUOUS)
    start = Tenor.parse("1Y").add_to(ref)
    end = Tenor.parse("18M").add_to(ref)
    fra = Fra(reference_date=ref, start_tenor=Tenor.parse("1Y"), end_tenor=Tenor.parse("18M"), quote=Decimal("0"))
    expected = curve.forward_rate(start, end)
    assert float(fra.par_rate(curve)) == pytest.approx(float(expected), abs=1e-12)


def test_swap_par_rate_flat_curve_matches_flat_rate() -> None:
    ref, curve = _flat_curve(0.04, compounding=Compounding.SEMI_ANNUAL)
    swap = Swap(reference_date=ref, tenor=Tenor.parse("5Y"), quote=Decimal("0"), fixed_frequency=Frequency.SEMI_ANNUAL)
    assert float(swap.par_rate(curve)) == pytest.approx(0.04, abs=1e-5)


def test_ois_par_rate_flat_curve_matches_flat_rate() -> None:
    ref, curve = _flat_curve(0.03, compounding=Compounding.SEMI_ANNUAL)
    ois = Ois(reference_date=ref, tenor=Tenor.parse("3Y"), quote=Decimal("0"), fixed_frequency=Frequency.SEMI_ANNUAL)
    assert float(ois.par_rate(curve)) == pytest.approx(0.03, abs=1e-5)


def test_instrument_set_ordering_and_duplicates() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    dep1 = Deposit(reference_date=ref, tenor=Tenor.parse("6M"), quote=Decimal("0.02"))
    dep2 = Deposit(reference_date=ref, tenor=Tenor.parse("3M"), quote=Decimal("0.02"))

    with pytest.raises(InvalidCurveInput):
        InstrumentSet([dep1, dep2])

    dep3 = Deposit(reference_date=ref, tenor=Tenor.parse("6M"), quote=Decimal("0.02"))
    with pytest.raises(InvalidCurveInput):
        InstrumentSet([dep1, dep3])
