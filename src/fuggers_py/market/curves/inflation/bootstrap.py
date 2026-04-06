"""Bootstrap inflation-index curves from zero-coupon inflation swaps."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Date
from fuggers_py.core import InstrumentId
from fuggers_py.reference.inflation.reference_index import reference_cpi

from ..discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from ..value_type import ValueType
from .curve import InflationIndexCurve

if TYPE_CHECKING:
    from fuggers_py.products.rates import ZeroCouponInflationSwap


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class InflationBootstrapPoint:
    """Single calibrated point on a bootstrapped inflation curve."""

    instrument_id: InstrumentId | None
    maturity_date: Date
    maturity_tenor: Decimal
    projected_index_ratio: Decimal
    projected_reference_cpi: Decimal
    market_fixed_rate: Decimal
    fitted_fixed_rate: Decimal
    residual_pv: Decimal

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        for field_name in (
            "maturity_tenor",
            "projected_index_ratio",
            "projected_reference_cpi",
            "market_fixed_rate",
            "fitted_fixed_rate",
            "residual_pv",
        ):
            object.__setattr__(self, field_name, _to_decimal(getattr(self, field_name)))


@dataclass(frozen=True, slots=True)
class InflationBootstrapResult:
    """Result of bootstrapping an inflation-index projection curve."""

    curve: InflationIndexCurve
    points: tuple[InflationBootstrapPoint, ...]
    anchor_reference_cpi: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "anchor_reference_cpi", _to_decimal(self.anchor_reference_cpi))


def bootstrap_inflation_curve(
    swaps: Sequence["ZeroCouponInflationSwap"],
    *,
    fixing_source: object,
    discount_curve: YieldCurve,
) -> InflationBootstrapResult:
    """Bootstrap a projected inflation-index curve from ZC inflation swaps.

    Sprint 5 supports a deterministic USD CPI-style path with one shared
    ``effective_date`` and market quotes taken directly from each instrument's
    ``fixed_rate`` field.
    """

    instruments = tuple(swaps)
    if not instruments:
        raise ValueError("bootstrap_inflation_curve requires at least one zero-coupon inflation swap.")
    _validate_bootstrap_instruments(instruments)
    anchor_swap = instruments[0]
    anchor_reference_cpi = reference_cpi(
        anchor_swap.effective_date,
        anchor_swap.inflation_convention,
        fixing_source,
    )
    reference_date = anchor_swap.effective_date
    day_count = DayCountConvention.ACT_365_FIXED.to_day_count()
    tenors = [0.0]
    ratios = [1.0]
    for swap in instruments:
        ratio = Decimal(1) + swap.fixed_rate
        if ratio <= Decimal(0):
            raise ValueError(
                f"bootstrap_inflation_curve requires positive projected index ratios; got {ratio} for {swap.instrument_id}."
            )
        tenor = day_count.year_fraction(reference_date, swap.maturity_date)
        tenors.append(float(tenor))
        ratios.append(float(ratio))
    curve = InflationIndexCurve(
        reference_date=reference_date,
        anchor_reference_cpi=anchor_reference_cpi,
        convention=anchor_swap.inflation_convention,
        curve=DiscreteCurve(
            reference_date,
            tenors=tenors,
            values=ratios,
            value_type=ValueType.inflation_index_ratio(),
            interpolation_method=InterpolationMethod.LINEAR,
            extrapolation_method=ExtrapolationMethod.FLAT,
        ),
    )
    from fuggers_py.pricers.rates.inflation_swap_pricer import InflationSwapPricer

    pricer = InflationSwapPricer()
    points = []
    for swap in instruments:
        pricing = pricer.price(
            swap,
            discount_curve=discount_curve,
            inflation_projection=curve,
        )
        ratio = curve.projected_index_ratio(swap.maturity_date, reference_date)
        points.append(
            InflationBootstrapPoint(
                instrument_id=swap.instrument_id,
                maturity_date=swap.maturity_date,
                maturity_tenor=day_count.year_fraction(reference_date, swap.maturity_date),
                projected_index_ratio=ratio,
                projected_reference_cpi=curve.projected_reference_cpi(swap.maturity_date),
                market_fixed_rate=swap.fixed_rate,
                fitted_fixed_rate=pricing.par_fixed_rate,
                residual_pv=pricing.present_value,
            )
        )
    return InflationBootstrapResult(
        curve=curve,
        points=tuple(points),
        anchor_reference_cpi=anchor_reference_cpi,
    )


def _validate_bootstrap_instruments(swaps: tuple["ZeroCouponInflationSwap", ...]) -> None:
    from fuggers_py.products.rates import ZeroCouponInflationSwap

    anchor = swaps[0]
    last_maturity = anchor.maturity_date
    for index, swap in enumerate(swaps):
        if not isinstance(swap, ZeroCouponInflationSwap):
            raise ValueError("bootstrap_inflation_curve only supports ZeroCouponInflationSwap instruments.")
        if swap.inflation_convention != anchor.inflation_convention:
            raise ValueError("bootstrap_inflation_curve requires a single shared inflation convention.")
        if swap.currency != anchor.currency:
            raise ValueError("bootstrap_inflation_curve requires a single shared currency.")
        if swap.effective_date != anchor.effective_date:
            raise ValueError(
                "bootstrap_inflation_curve requires all calibration swaps to share the same effective_date in Sprint 5."
            )
        if index > 0 and swap.maturity_date <= last_maturity:
            raise ValueError("bootstrap_inflation_curve requires strictly increasing maturity ordering.")
        last_maturity = swap.maturity_date


__all__ = [
    "InflationBootstrapPoint",
    "InflationBootstrapResult",
    "bootstrap_inflation_curve",
]
