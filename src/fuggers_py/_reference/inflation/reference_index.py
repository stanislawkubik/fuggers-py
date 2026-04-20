"""Daily reference-index helpers built from monthly inflation fixings.

The helpers in this module resolve a daily reference CPI from monthly fixing
data using the observation lag and interpolation policy defined by an
inflation convention.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py._core.types import Date
from fuggers_py._inflation_types import InflationInterpolation
from fuggers_py._market.snapshot import InflationFixing, MarketDataSnapshot
from fuggers_py._market.sources import InflationFixingSource, MarketDataProvider
from fuggers_py._core.ids import YearMonth

from .conventions import InflationConvention
from .errors import InvalidObservationLag, MissingInflationFixing, UnsupportedInflationInterpolation


InflationFixingSourceLike = InflationFixingSource | MarketDataProvider | MarketDataSnapshot


def _year_month(value: Date) -> YearMonth:
    return YearMonth(value.year(), value.month())


def _resolve_fixing_source(fixing_source: InflationFixingSourceLike) -> InflationFixingSource:
    if isinstance(fixing_source, MarketDataSnapshot):
        return fixing_source.inflation_fixing_source()
    if isinstance(fixing_source, InflationFixingSource | MarketDataProvider):
        return fixing_source
    if hasattr(fixing_source, "get_inflation_fixing"):
        return fixing_source  # type: ignore[return-value]
    raise TypeError("fixing_source must provide get_inflation_fixing() or be a MarketDataSnapshot.")


def _validate_observation_lag(observation_lag_months: int) -> None:
    if observation_lag_months < 0:
        raise InvalidObservationLag(observation_lag_months)


def _lookup_fixing(
    observation_month: YearMonth,
    *,
    convention: InflationConvention,
    fixing_source: InflationFixingSource,
) -> InflationFixing | None:
    for index_name in convention.lookup_names():
        fixing = fixing_source.get_inflation_fixing(index_name, observation_month)
        if fixing is not None:
            return fixing
    return None


def _require_fixings(
    observation_months: tuple[YearMonth, ...],
    *,
    settlement_date: Date,
    convention: InflationConvention,
    fixing_source: InflationFixingSource,
) -> tuple[InflationFixing, ...]:
    resolved: list[InflationFixing] = []
    missing: list[YearMonth] = []

    for observation_month in observation_months:
        fixing = _lookup_fixing(
            observation_month,
            convention=convention,
            fixing_source=fixing_source,
        )
        if fixing is None:
            missing.append(observation_month)
            continue
        resolved.append(fixing)

    if missing:
        raise MissingInflationFixing(
            index_name=convention.index_source,
            requested_date=settlement_date,
            observation_months=tuple(missing),
        )
    return tuple(resolved)


def reference_cpi(
    settlement_date: Date,
    convention: InflationConvention,
    fixing_source: InflationFixingSourceLike,
) -> Decimal:
    """Return the daily reference CPI implied by monthly published fixings.

    Monthly conventions use the fixing for the lagged observation month. Linear
    conventions interpolate between the lagged month and the following month,
    with the first day of the month pinned to the first fixing.
    """

    _validate_observation_lag(convention.observation_lag_months)
    resolved_source = _resolve_fixing_source(fixing_source)
    month_start = settlement_date.start_of_month()
    first_month = _year_month(month_start.add_months(-convention.observation_lag_months))

    if convention.interpolation_method is InflationInterpolation.MONTHLY:
        fixing = _require_fixings(
            (first_month,),
            settlement_date=settlement_date,
            convention=convention,
            fixing_source=resolved_source,
        )[0]
        return fixing.value

    if convention.interpolation_method is InflationInterpolation.LINEAR:
        second_month = _year_month(month_start.add_months(1 - convention.observation_lag_months))
        first_fixing, second_fixing = _require_fixings(
            (first_month, second_month),
            settlement_date=settlement_date,
            convention=convention,
            fixing_source=resolved_source,
        )
        if settlement_date.day() == 1:
            return first_fixing.value

        month_length = Decimal(settlement_date.days_in_month())
        day_offset = Decimal(settlement_date.day() - 1)
        weight = day_offset / month_length
        return first_fixing.value + (second_fixing.value - first_fixing.value) * weight

    raise UnsupportedInflationInterpolation(convention.interpolation_method)


def reference_index_ratio(
    settlement_date: Date,
    base_date: Date,
    convention: InflationConvention,
    fixing_source: InflationFixingSourceLike,
) -> Decimal:
    """Return the ratio of reference CPI at settlement and base dates."""

    settlement_reference = reference_cpi(settlement_date, convention, fixing_source)
    base_reference = reference_cpi(base_date, convention, fixing_source)
    return settlement_reference / base_reference


__all__ = ["reference_cpi", "reference_index_ratio"]
