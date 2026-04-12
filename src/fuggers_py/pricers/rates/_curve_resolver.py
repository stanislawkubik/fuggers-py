"""Internal curve resolution and bump helpers for rates pricing."""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Currency, Date
from fuggers_py.market.curve_support import (
    discount_factor_at_date,
    key_rate_bumped_curve,
    parallel_bumped_curve,
    zero_rate_at_date,
)
from fuggers_py.market.curves import DiscountingCurve
from fuggers_py.market.curves.multicurve import RateIndex
from fuggers_py.market.state import AnalyticsCurves


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _curve_supports_discounting(curve: object | None) -> bool:
    return isinstance(curve, DiscountingCurve)


def _curve_supports_forward_projection(curve: object | None) -> bool:
    return curve is not None and hasattr(curve, "forward_rate")


def _curve_supports_projection(curve: object | None) -> bool:
    return _curve_supports_discounting(curve) or _curve_supports_forward_projection(curve)


def _curve_supports_inflation_projection(curve: object | None) -> bool:
    return curve is not None and (
        hasattr(curve, "projected_reference_cpi")
        or hasattr(curve, "projected_index_ratio")
        or hasattr(curve, "reference_cpi")
        or hasattr(curve, "get_reference_cpi")
        or hasattr(curve, "get_inflation_fixing")
    )


def _projection_keys(currency: Currency, index_name: str, index_tenor: Tenor | None) -> tuple[str, ...]:
    normalized_name = index_name.strip().upper()
    if index_tenor is None:
        return (
            normalized_name,
            f"{currency.code()}-{normalized_name}",
        )
    rate_index = RateIndex.new(normalized_name, index_tenor, currency)
    return (
        str(rate_index),
        rate_index.key(),
        normalized_name,
        f"{normalized_name}-{index_tenor}",
        f"{currency.code()}-{normalized_name}",
        f"{currency.code()}-{normalized_name}-{index_tenor}",
    )


def _inflation_projection_keys(convention) -> tuple[str, ...]:
    normalized_name = convention.name.strip().upper().replace(" ", "_").replace("-", "_")
    family = convention.family.strip().upper()
    index_source = convention.index_source.strip().upper()
    currency = convention.currency.code()
    ordered: dict[str, None] = {}
    for key in (
        index_source,
        family,
        normalized_name,
        "INFLATION",
        "CPI",
        f"{currency}-{index_source}",
        f"{currency}-{family}",
        f"{currency}-INFLATION",
    ):
        if key:
            ordered[key] = None
    for alias in convention.lookup_names():
        normalized = alias.strip().upper().replace(" ", "_").replace("-", "_")
        if normalized:
            ordered[normalized] = None
            ordered[f"{currency}-{normalized}"] = None
    return tuple(ordered)


def forward_rate_from_curve(
    curve: object,
    start_date: Date,
    end_date: Date,
    *,
    day_count_convention: DayCountConvention,
) -> Decimal:
    """Return the forward rate implied by a projection or discount curve.

    The rate is a raw decimal. When the curve only exposes discount factors,
    the forward is computed from the start and end discount factors using the
    supplied day-count convention.
    """

    if _curve_supports_forward_projection(curve) and not _curve_supports_discounting(curve):
        return _to_decimal(curve.forward_rate(start_date, end_date))
    tau = day_count_convention.to_day_count().year_fraction(start_date, end_date)
    if tau == Decimal(0):
        raise ValueError("forward_rate requires distinct start and end dates.")
    df_start = discount_factor_at_date(curve, start_date)
    df_end = discount_factor_at_date(curve, end_date)
    if df_end == Decimal(0):
        raise ValueError("forward_rate requires a non-zero end-date discount factor.")
    return (df_start / df_end - Decimal(1)) / tau


def resolve_discount_curve(curves: AnalyticsCurves, currency: Currency) -> DiscountingCurve:
    """Return the discount curve used for the given currency."""

    environment = curves.multicurve_environment
    if environment is not None and hasattr(environment, "discount_curve"):
        curve = environment.discount_curve(currency)
        if _curve_supports_discounting(curve):
            return curve
    if _curve_supports_discounting(curves.discount_curve):
        return curves.discount_curve
    if _curve_supports_discounting(curves.collateral_curve):
        return curves.collateral_curve
    raise ValueError(f"Missing discount curve for currency {currency.code()}.")


def resolve_projection_curve(
    curves: AnalyticsCurves,
    *,
    currency: Currency,
    index_name: str,
    index_tenor: Tenor | None,
) -> object:
    """Return the projection curve for the supplied rate index."""

    environment = curves.multicurve_environment
    if environment is not None and index_tenor is not None and hasattr(environment, "projection_curve"):
        curve = environment.projection_curve(RateIndex.new(index_name, index_tenor, currency))
        if _curve_supports_projection(curve):
            return curve
    for key in _projection_keys(currency, index_name, index_tenor):
        curve = curves.projection_curves.get(key)
        if _curve_supports_projection(curve):
            return curve
    if _curve_supports_projection(curves.forward_curve):
        return curves.forward_curve
    if _curve_supports_discounting(curves.discount_curve):
        return curves.discount_curve
    raise ValueError(f"Missing projection curve for {currency.code()} {index_name}.")


def resolve_inflation_projection(curves: AnalyticsCurves, *, convention) -> object:
    """Return the inflation projection object for an inflation-linked product."""

    if _curve_supports_inflation_projection(curves.inflation_curve):
        return curves.inflation_curve
    for key in _inflation_projection_keys(convention):
        curve = curves.inflation_curves.get(key)
        if curve is not None:
            return curve
        lowered = key.lower()
        for candidate_key, candidate_value in curves.inflation_curves.items():
            if str(candidate_key).lower() == lowered:
                return candidate_value
    for key in _inflation_projection_keys(convention):
        curve = curves.projection_curves.get(key)
        if curve is not None:
            return curve
        lowered = key.lower()
        for candidate_key, candidate_value in curves.projection_curves.items():
            if str(candidate_key).lower() == lowered:
                return candidate_value
    if _curve_supports_inflation_projection(curves.forward_curve):
        return curves.forward_curve
    raise ValueError(
        f"Missing inflation projection for {convention.currency.code()} {convention.index_source}."
    )


def _parallel_bump_curve(curve: object | None, amount: float) -> object | None:
    if _curve_supports_discounting(curve):
        return parallel_bumped_curve(curve, amount)
    return curve


def _key_rate_bump_curve(curve: object | None, tenor_grid: tuple[Tenor, ...], key_tenor: Tenor, bump: float) -> object | None:
    if _curve_supports_discounting(curve):
        return key_rate_bumped_curve(curve, tenor_grid=tenor_grid, key_tenor=key_tenor, bump=bump)
    return curve


def analytics_curves_with_parallel_bump(
    curves: AnalyticsCurves,
    *,
    currency: Currency,
    projection_indices: tuple[RateIndex, ...],
    bump: Decimal,
) -> AnalyticsCurves:
    """Return a copy of ``curves`` with a parallel rate bump applied.

    The bump is applied to the discount curve for ``currency`` and to any
    matching projection curves. The bump is expressed as a raw decimal shift.
    """

    amount = float(bump)
    environment = curves.multicurve_environment
    bumped_environment = environment
    if environment is not None and hasattr(environment, "discount_curves") and hasattr(environment, "projection_curves"):
        discount_curves = dict(environment.discount_curves)
        if currency in discount_curves:
            discount_curves[currency] = _parallel_bump_curve(discount_curves[currency], amount)
        projection_curves = dict(environment.projection_curves)
        for index in projection_indices:
            if index in projection_curves:
                projection_curves[index] = _parallel_bump_curve(projection_curves[index], amount)
        bumped_environment = type(environment)(
            discount_curves=discount_curves,
            projection_curves=projection_curves,
        )
    bumped_projection_curves = {
        key: _parallel_bump_curve(value, amount)
        for key, value in curves.projection_curves.items()
    }
    return AnalyticsCurves(
        discount_curve=_parallel_bump_curve(curves.discount_curve, amount),
        forward_curve=_parallel_bump_curve(curves.forward_curve, amount),
        government_curve=curves.government_curve,
        benchmark_curve=curves.benchmark_curve,
        credit_curve=curves.credit_curve,
        repo_curve=curves.repo_curve,
        collateral_curve=_parallel_bump_curve(curves.collateral_curve, amount),
        fx_forward_curve=curves.fx_forward_curve,
        multicurve_environment=bumped_environment,
        projection_curves=bumped_projection_curves,
        inflation_curve=curves.inflation_curve,
        inflation_curves=curves.inflation_curves,
        vol_surface=curves.vol_surface,
    )


def analytics_curves_with_key_rate_bump(
    curves: AnalyticsCurves,
    *,
    currency: Currency,
    projection_indices: tuple[RateIndex, ...],
    tenor_grid: tuple[Tenor, ...],
    key_tenor: Tenor,
    bump: Decimal,
) -> AnalyticsCurves:
    """Return a copy of ``curves`` with a key-rate bump applied.

    The bump is applied at ``key_tenor`` using the supplied tenor grid. The
    amount is a raw decimal shift.
    """

    environment = curves.multicurve_environment
    bumped_environment = environment
    if environment is not None and hasattr(environment, "discount_curves") and hasattr(environment, "projection_curves"):
        discount_curves = dict(environment.discount_curves)
        if currency in discount_curves:
            discount_curves[currency] = _key_rate_bump_curve(discount_curves[currency], tenor_grid, key_tenor, float(bump))
        projection_curves = dict(environment.projection_curves)
        for index in projection_indices:
            if index in projection_curves:
                projection_curves[index] = _key_rate_bump_curve(
                    projection_curves[index],
                    tenor_grid,
                    key_tenor,
                    float(bump),
                )
        bumped_environment = type(environment)(
            discount_curves=discount_curves,
            projection_curves=projection_curves,
        )
    bumped_projection_curves = {
        key: _key_rate_bump_curve(value, tenor_grid, key_tenor, float(bump))
        for key, value in curves.projection_curves.items()
    }
    return AnalyticsCurves(
        discount_curve=_key_rate_bump_curve(curves.discount_curve, tenor_grid, key_tenor, float(bump)),
        forward_curve=_key_rate_bump_curve(curves.forward_curve, tenor_grid, key_tenor, float(bump)),
        government_curve=curves.government_curve,
        benchmark_curve=curves.benchmark_curve,
        credit_curve=curves.credit_curve,
        repo_curve=curves.repo_curve,
        collateral_curve=_key_rate_bump_curve(curves.collateral_curve, tenor_grid, key_tenor, float(bump)),
        fx_forward_curve=curves.fx_forward_curve,
        multicurve_environment=bumped_environment,
        projection_curves=bumped_projection_curves,
        inflation_curve=curves.inflation_curve,
        inflation_curves=curves.inflation_curves,
        vol_surface=curves.vol_surface,
    )


def curve_zero_rate(curve: DiscountingCurve, date: Date) -> Decimal:
    """Return the curve zero rate as a raw decimal."""

    return zero_rate_at_date(curve, date)


__all__ = [
    "analytics_curves_with_key_rate_bump",
    "analytics_curves_with_parallel_bump",
    "curve_zero_rate",
    "forward_rate_from_curve",
    "resolve_discount_curve",
    "resolve_inflation_projection",
    "resolve_projection_curve",
]
