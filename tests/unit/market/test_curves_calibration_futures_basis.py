from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core import Compounding, Date
from fuggers_py.market.curves import ZeroCurveBuilder
from fuggers_py.market.curves.calibration import BasisSwap, Future
from fuggers_py.market.curves.errors import InvalidCurveInput


def _flat_curve(rate: str):
    ref = Date.from_ymd(2024, 1, 1)
    curve = (
        ZeroCurveBuilder(reference_date=ref, compounding=Compounding.CONTINUOUS)
        .add_rate(ref.add_days(365), Decimal(rate))
        .add_rate(ref.add_days(365 * 10), Decimal(rate))
        .build()
    )
    return ref, curve


def test_future_par_rate_matches_forward_on_flat_curve() -> None:
    ref, curve = _flat_curve("0.04")
    future = Future(
        reference_date=ref,
        quote=Decimal("96.0"),
        start_tenor=Tenor.parse("1Y"),
        end_tenor=Tenor.parse("15M"),
        convexity_adjustment_bps=Decimal("0"),
    )
    start = Tenor.parse("1Y").add_to(ref)
    end = Tenor.parse("15M").add_to(ref)
    assert float(future.par_rate(curve)) == pytest.approx(float(curve.forward_rate(start, end)), abs=1e-12)


def test_basis_swap_par_basis_is_zero_on_identical_curves() -> None:
    ref, curve = _flat_curve("0.035")
    basis_swap = BasisSwap(reference_date=ref, tenor=Tenor.parse("5Y"), quote=Decimal("0"))
    assert float(basis_swap.par_basis(curve, curve)) == pytest.approx(0.0, abs=1e-12)


def test_future_rejects_negative_or_zero_tenor_inputs() -> None:
    ref, _ = _flat_curve("0.04")
    with pytest.raises(InvalidCurveInput):
        Future(reference_date=ref, quote=Decimal("96.0"), start_date=ref.add_years(1), end_date=ref.add_years(1))
    with pytest.raises(InvalidCurveInput):
        Future(reference_date=ref, quote=Decimal("96.0"), start_date=ref.add_years(2), end_date=ref.add_years(1))
