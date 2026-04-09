"""Nearby-bond benchmark basket helpers for fitted bond-curve analytics.

These utilities intentionally build a weighted basket of nearby fitted bonds.
They remain useful as an audit or benchmark basket, but they are not the
canonical constant-maturity curve implementation. Direct constant-maturity
par yields should come from ``fitted_bonds.par_curve`` instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from .bond_curve import BondCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class BenchmarkComponent:
    """Single fitted bond component used in a notional benchmark.

    The component keeps the weighting inputs visible so the benchmark can be
    audited back to the selected fitted bonds.
    """

    instrument_id: object
    weight: Decimal
    maturity_years: Decimal
    amount_outstanding: Decimal
    liquidity_score: Decimal
    benchmark_flag: bool
    fair_value_clean_price: Decimal
    fair_value_yield: Decimal


@dataclass(frozen=True, slots=True)
class NotionalBenchmark:
    """Aggregated nearby-bond benchmark basket result.

    The benchmark is a weighted basket of fitted bonds, along with the target
    maturity and the weighted fair-value outputs used to summarize it.
    """

    target_maturity_years: Decimal
    weighted_maturity_years: Decimal
    weighted_fair_value_clean_price: Decimal
    weighted_fair_value_yield: Decimal
    components: tuple[BenchmarkComponent, ...]


def build_notional_benchmark(
    fit_result: BondCurve,
    target_maturity_years: object,
    *,
    component_count: int = 2,
    benchmark_only: bool = True,
) -> NotionalBenchmark:
    """Build a weighted nearby-bond benchmark basket from fitted results.

    Candidates are ranked by proximity to the target maturity, then weighted by
    amount outstanding and liquidity score before the selected fair values are
    aggregated into a representative basket. This helper is not the direct
    constant-maturity par-curve implementation.
    """
    target = _to_decimal(target_maturity_years)
    if component_count <= 0:
        raise ValueError("build_notional_benchmark requires a positive component_count.")

    candidates: list[Mapping[str, object]] = [point for point in fit_result.bonds if point.get("reference_data") is not None]
    if not candidates:
        raise ValueError("build_notional_benchmark requires reference_data on fitted bond points.")
    if benchmark_only and any(point.get("reference_data") and point["reference_data"].benchmark_flag for point in candidates):
        candidates = [point for point in candidates if point.get("reference_data") and point["reference_data"].benchmark_flag]

    scored: list[tuple[Decimal, Mapping[str, object]]] = []
    for point in candidates:
        reference_data = point.get("reference_data")
        assert reference_data is not None
        amount_outstanding = reference_data.amount_outstanding or Decimal(1)
        liquidity_score = reference_data.liquidity_score or Decimal(1)
        maturity_years = _to_decimal(point["maturity_years"])
        distance = abs(maturity_years - target)
        closeness = Decimal(1) / max(distance, Decimal("0.25"))
        score = closeness * amount_outstanding * liquidity_score
        scored.append((score, point))

    selected = [point for _, point in sorted(scored, key=lambda item: (-item[0], item[1]["instrument_id"].as_str()))[:component_count]]
    raw_weights: list[Decimal] = []
    for point in selected:
        reference_data = point.get("reference_data")
        assert reference_data is not None
        amount_outstanding = reference_data.amount_outstanding or Decimal(1)
        liquidity_score = reference_data.liquidity_score or Decimal(1)
        distance = abs(_to_decimal(point["maturity_years"]) - target)
        raw_weights.append((Decimal(1) / max(distance, Decimal("0.25"))) * amount_outstanding * liquidity_score)

    normalizer = sum(raw_weights, start=Decimal(0))
    components: list[BenchmarkComponent] = []
    weighted_maturity = Decimal(0)
    weighted_clean = Decimal(0)
    weighted_yield = Decimal(0)
    for raw_weight, point in zip(raw_weights, selected, strict=True):
        reference_data = point.get("reference_data")
        assert reference_data is not None
        weight = raw_weight / normalizer
        amount_outstanding = reference_data.amount_outstanding or Decimal(1)
        liquidity_score = reference_data.liquidity_score or Decimal(1)
        maturity_years = _to_decimal(point["maturity_years"])
        fair_value_clean_price = _to_decimal(point["fair_value_clean_price"])
        fitted_yield = _to_decimal(point["fitted_yield"])
        weighted_maturity += weight * maturity_years
        weighted_clean += weight * fair_value_clean_price
        weighted_yield += weight * fitted_yield
        components.append(
            BenchmarkComponent(
                instrument_id=point["instrument_id"],
                weight=weight,
                maturity_years=maturity_years,
                amount_outstanding=amount_outstanding,
                liquidity_score=liquidity_score,
                benchmark_flag=bool(reference_data.benchmark_flag),
                fair_value_clean_price=fair_value_clean_price,
                fair_value_yield=fitted_yield,
            )
        )
    return NotionalBenchmark(
        target_maturity_years=target,
        weighted_maturity_years=weighted_maturity,
        weighted_fair_value_clean_price=weighted_clean,
        weighted_fair_value_yield=weighted_yield,
        components=tuple(components),
    )


__all__ = ["BenchmarkComponent", "NotionalBenchmark", "build_notional_benchmark"]
