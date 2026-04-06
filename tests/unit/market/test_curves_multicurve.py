from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core.types import Compounding, Currency, Date
from fuggers_py.market.curves import ZeroCurveBuilder
from fuggers_py.market.curves.multicurve import MissingCurveError, MultiCurveEnvironmentBuilder, RateIndex


def _curve(ref: Date, rate: str) -> object:
    return (
        ZeroCurveBuilder(reference_date=ref, compounding=Compounding.CONTINUOUS)
        .add_rate(ref.add_days(365), Decimal(rate))
        .add_rate(ref.add_days(365 * 10), Decimal(rate))
        .build()
    )


def test_multicurve_environment_build_and_lookup() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    disc = _curve(ref, "0.03")
    proj_1m = _curve(ref, "0.031")
    proj_3m = _curve(ref, "0.032")

    idx_1m = RateIndex.new("SOFR", Tenor.parse("1M"), Currency.USD)
    idx_3m = RateIndex.new("LIBOR", Tenor.parse("3M"), Currency.USD)

    env = (
        MultiCurveEnvironmentBuilder()
        .add_discount_curve(Currency.USD, disc)
        .add_projection_curve(idx_1m, proj_1m)
        .add_projection_curve(idx_3m, proj_3m)
        .build()
    )

    assert env.discount_curve(Currency.USD) is disc
    assert env.projection_curve(idx_1m) is proj_1m
    assert env.projection_curve(idx_3m) is proj_3m

    with pytest.raises(MissingCurveError):
        env.discount_curve(Currency.EUR)
