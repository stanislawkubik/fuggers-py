"""Contribution and attribution helpers.

`attribution_summary` is a holdings-allocation helper, not a full factor or
Brinson attribution engine. It allocates portfolio duration and DV01 back to
holdings using the same portfolio market-value weights used in the portfolio
analytics layer, so the reported totals reconcile cleanly to the portfolio
summary.
"""

from __future__ import annotations

from decimal import Decimal

from ..analytics.base import PortfolioAnalytics
from ..portfolio import Portfolio
from .types import (
    AggregatedAttribution,
    AttributionInput,
    BucketContribution,
    HoldingAttribution,
    PortfolioAttribution,
    SectorAttribution,
)
from .risk import top_contributors


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _effective_assumptions(assumptions: AttributionInput | None) -> AttributionInput:
    return assumptions or AttributionInput()


def _position_name(position: object) -> str | None:
    if hasattr(position, "name"):
        return position.name()
    label = getattr(position, "label", None)
    return None if label is None else str(label)


def _sector_name(position: object | None) -> str:
    if position is None:
        return "UNCLASSIFIED"
    sector_info = getattr(position, "sector_info", None)
    if sector_info is not None and getattr(sector_info, "sector", None) is not None:
        sector = sector_info.sector
        return getattr(sector, "value", str(sector))
    classification = getattr(position, "classification", None)
    if classification is not None and getattr(classification, "sector", None) is not None:
        sector = classification.sector
        return getattr(sector, "value", str(sector))
    return "UNCLASSIFIED"


def _weighted_metric_by_sector(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    metric_name: str,
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    analytics = PortfolioAnalytics(portfolio)
    metrics = analytics.metrics(curve, settlement_date)
    positions = analytics.position_metrics(curve, settlement_date)
    originals = {
        name: position
        for position in portfolio.positions
        if (name := _position_name(position)) is not None
    }
    sector_values: dict[str, Decimal] = {}
    sector_weights: dict[str, Decimal] = {}
    for item in positions:
        sector = _sector_name(originals.get(item.name))
        weight = metrics.weights.get(item.name, Decimal(0))
        metric_value = getattr(item, metric_name) or Decimal(0)
        sector_values[sector] = sector_values.get(sector, Decimal(0)) + (metric_value * weight)
        sector_weights[sector] = sector_weights.get(sector, Decimal(0)) + weight
    return sector_values, sector_weights


def _sector_difference(
    portfolio: Portfolio,
    benchmark: Portfolio,
    *,
    curve,
    settlement_date,
    metric_name: str,
    metric_label: str,
) -> SectorAttribution:
    portfolio_values, portfolio_weights = _weighted_metric_by_sector(
        portfolio,
        curve=curve,
        settlement_date=settlement_date,
        metric_name=metric_name,
    )
    benchmark_values, benchmark_weights = _weighted_metric_by_sector(
        benchmark,
        curve=curve,
        settlement_date=settlement_date,
        metric_name=metric_name,
    )
    keys = sorted(set(portfolio_values) | set(benchmark_values) | set(portfolio_weights) | set(benchmark_weights))
    entries = tuple(
        BucketContribution(
            name=key,
            portfolio_value=portfolio_values.get(key, Decimal(0)),
            benchmark_value=benchmark_values.get(key, Decimal(0)),
            active_value=portfolio_values.get(key, Decimal(0)) - benchmark_values.get(key, Decimal(0)),
            portfolio_weight=portfolio_weights.get(key, Decimal(0)),
            benchmark_weight=benchmark_weights.get(key, Decimal(0)),
            active_weight=portfolio_weights.get(key, Decimal(0)) - benchmark_weights.get(key, Decimal(0)),
        )
        for key in keys
    )
    return SectorAttribution(
        entries=entries,
        metric=metric_label,
        portfolio_total=sum((entry.portfolio_value for entry in entries), Decimal(0)),
        benchmark_total=sum((entry.benchmark_value for entry in entries), Decimal(0)),
        active_total=sum((entry.active_value for entry in entries), Decimal(0)),
    )


def attribution_summary(portfolio: Portfolio, *, curve, settlement_date) -> PortfolioAttribution:
    """Return holding-level PV and DV01 attribution.

    The PV and DV01 percentages are normalized against the portfolio totals
    computed by the analytics layer. The duration contribution is adjusted so
    the holding totals reconcile to the portfolio-level duration.
    """

    analytics = PortfolioAnalytics(portfolio)
    metrics = analytics.position_metrics(curve, settlement_date)
    portfolio_metrics = analytics.metrics(curve, settlement_date)
    total_dirty = portfolio_metrics.dirty_pv
    total_dv01 = portfolio_metrics.dv01
    results: list[HoldingAttribution] = []
    for item in metrics:
        pv_pct = Decimal(0) if total_dirty == 0 else item.dirty_value / total_dirty
        dv01_pct = Decimal(0) if total_dv01 == 0 else item.dv01 / total_dv01
        results.append(
            HoldingAttribution(
                name=item.name,
                pv_pct=pv_pct,
                dv01_pct=dv01_pct,
                duration_contribution=item.duration * pv_pct,
            )
        )
    if results:
        duration_total = sum((entry.duration_contribution for entry in results), Decimal(0))
        duration_delta = portfolio_metrics.duration - duration_total
        if duration_delta != 0:
            last = results[-1]
            results[-1] = HoldingAttribution(
                name=last.name,
                pv_pct=last.pv_pct,
                dv01_pct=last.dv01_pct,
                duration_contribution=last.duration_contribution + duration_delta,
            )
    return PortfolioAttribution(
        entries=tuple(results),
        total_pv_pct=sum((entry.pv_pct for entry in results), Decimal(0)),
        total_dv01_pct=sum((entry.dv01_pct for entry in results), Decimal(0)),
        total_duration_contribution=sum((entry.duration_contribution for entry in results), Decimal(0)),
    )


def calculate_attribution(portfolio: Portfolio, *, curve, settlement_date) -> PortfolioAttribution:
    """Compatibility alias for :func:`attribution_summary`."""

    return attribution_summary(portfolio, curve=curve, settlement_date=settlement_date)


def estimate_income_returns(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    horizon_years: Decimal | None = None,
    assumptions: AttributionInput | None = None,
) -> Decimal:
    """Estimate income return over the provided horizon as a raw decimal.

    The estimate is the portfolio current yield multiplied by the horizon in
    years.
    """

    active_assumptions = _effective_assumptions(assumptions)
    years = active_assumptions.income_horizon_years if horizon_years is None else _to_decimal(horizon_years)
    if years < 0:
        raise ValueError("horizon_years must be non-negative.")
    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    return metrics.current_yield * years


def estimate_rate_returns(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    rate_change_bps: Decimal | None = None,
    assumptions: AttributionInput | None = None,
) -> Decimal:
    """Estimate rate return from a parallel move in raw decimal terms.

    The result is a first-order estimate based on portfolio DV01 and the
    requested rate shock.
    """

    active_assumptions = _effective_assumptions(assumptions)
    bump_bps = active_assumptions.rate_change_bps if rate_change_bps is None else _to_decimal(rate_change_bps)
    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    if metrics.dirty_pv == 0:
        return Decimal(0)
    return -(metrics.dv01 * bump_bps) / metrics.dirty_pv


def estimate_spread_returns(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    spread_change_bps: Decimal | None = None,
    assumptions: AttributionInput | None = None,
) -> Decimal:
    """Estimate spread return from a spread move in raw decimal terms.

    The result is a first-order estimate based on portfolio CS01 and the
    requested spread shock.
    """

    active_assumptions = _effective_assumptions(assumptions)
    bump_bps = active_assumptions.spread_change_bps if spread_change_bps is None else _to_decimal(spread_change_bps)
    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    if metrics.dirty_pv == 0:
        return Decimal(0)
    return -(metrics.cs01 * bump_bps) / metrics.dirty_pv


def duration_difference_by_sector(
    portfolio: Portfolio,
    benchmark: Portfolio,
    *,
    curve,
    settlement_date,
) -> SectorAttribution:
    """Return sector-level duration differences versus benchmark."""

    return _sector_difference(
        portfolio,
        benchmark,
        curve=curve,
        settlement_date=settlement_date,
        metric_name="duration",
        metric_label="duration",
    )


def spread_difference_by_sector(
    portfolio: Portfolio,
    benchmark: Portfolio,
    *,
    curve,
    settlement_date,
) -> SectorAttribution:
    """Return sector-level spread differences versus benchmark."""

    return _sector_difference(
        portfolio,
        benchmark,
        curve=curve,
        settlement_date=settlement_date,
        metric_name="z_spread",
        metric_label="spread",
    )


def aggregated_attribution(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    assumptions: AttributionInput | None = None,
    benchmark: Portfolio | None = None,
) -> AggregatedAttribution:
    """Return aggregated income, rate, and spread attribution.

    When a benchmark is supplied, active attribution fields are populated as
    portfolio minus benchmark.
    """

    active_assumptions = _effective_assumptions(assumptions)
    income = estimate_income_returns(portfolio, curve=curve, settlement_date=settlement_date, assumptions=active_assumptions)
    rate = estimate_rate_returns(portfolio, curve=curve, settlement_date=settlement_date, assumptions=active_assumptions)
    spread = estimate_spread_returns(portfolio, curve=curve, settlement_date=settlement_date, assumptions=active_assumptions)
    total = income + rate + spread
    if benchmark is None:
        return AggregatedAttribution(
            assumptions=active_assumptions,
            income_return=income,
            rate_return=rate,
            spread_return=spread,
            total_return=total,
        )

    benchmark_income = estimate_income_returns(
        benchmark,
        curve=curve,
        settlement_date=settlement_date,
        assumptions=active_assumptions,
    )
    benchmark_rate = estimate_rate_returns(
        benchmark,
        curve=curve,
        settlement_date=settlement_date,
        assumptions=active_assumptions,
    )
    benchmark_spread = estimate_spread_returns(
        benchmark,
        curve=curve,
        settlement_date=settlement_date,
        assumptions=active_assumptions,
    )
    benchmark_total = benchmark_income + benchmark_rate + benchmark_spread
    return AggregatedAttribution(
        assumptions=active_assumptions,
        income_return=income,
        rate_return=rate,
        spread_return=spread,
        total_return=total,
        benchmark_income_return=benchmark_income,
        benchmark_rate_return=benchmark_rate,
        benchmark_spread_return=benchmark_spread,
        benchmark_total_return=benchmark_total,
        active_income_return=income - benchmark_income,
        active_rate_return=rate - benchmark_rate,
        active_spread_return=spread - benchmark_spread,
        active_total_return=total - benchmark_total,
        duration_by_sector=duration_difference_by_sector(
            portfolio,
            benchmark,
            curve=curve,
            settlement_date=settlement_date,
        ),
        spread_by_sector=spread_difference_by_sector(
            portfolio,
            benchmark,
            curve=curve,
            settlement_date=settlement_date,
        ),
    )


def weights_sum_check(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return the sum of portfolio weights under the requested weighting basis."""

    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    return sum(metrics.weights.values(), Decimal(0))


__all__ = [
    "AggregatedAttribution",
    "AttributionInput",
    "BucketContribution",
    "HoldingAttribution",
    "PortfolioAttribution",
    "SectorAttribution",
    "aggregated_attribution",
    "attribution_summary",
    "calculate_attribution",
    "duration_difference_by_sector",
    "estimate_income_returns",
    "estimate_rate_returns",
    "estimate_spread_returns",
    "spread_difference_by_sector",
    "top_contributors",
    "weights_sum_check",
]
