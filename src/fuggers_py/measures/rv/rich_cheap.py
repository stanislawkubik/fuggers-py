"""Local rich/cheap ranking from fitted bond-curve residuals.

The residuals are expressed in basis points. Positive yield residuals mean the
bond screens cheap; negative residuals mean the bond screens rich.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.market.curves.fitted_bonds import BondCurve


@dataclass(frozen=True, slots=True)
class RichCheapSignal:
    """Ranked rich/cheap signal derived from fitted bond residuals."""

    instrument_id: object
    rank: int
    classification: str
    cheapness_bps: Decimal
    price_residual: Decimal
    bp_residual: Decimal
    z_score: Decimal


def rank_rich_cheap(
    fit_result: BondCurve,
    *,
    threshold_bps: object = Decimal(0),
) -> tuple[RichCheapSignal, ...]:
    """Rank fitted bonds from cheapest to richest using basis-point residuals."""
    threshold = threshold_bps if isinstance(threshold_bps, Decimal) else Decimal(str(threshold_bps))
    residuals = [
        point["bp_residual"] if isinstance(point["bp_residual"], Decimal) else Decimal(str(point["bp_residual"]))
        for point in fit_result.bonds
    ]
    mean = sum(residuals, start=Decimal(0)) / Decimal(len(residuals))
    variance = sum((residual - mean) ** 2 for residual in residuals) / Decimal(len(residuals))
    std = variance.sqrt() if variance > Decimal(0) else Decimal(0)

    ordered = sorted(
        fit_result.bonds,
        key=lambda point: (
            point["bp_residual"] if isinstance(point["bp_residual"], Decimal) else Decimal(str(point["bp_residual"])),
            -(
                point["price_residual"]
                if isinstance(point["price_residual"], Decimal)
                else Decimal(str(point["price_residual"]))
            ),
            point["instrument_id"].as_str(),
        ),
        reverse=True,
    )
    signals: list[RichCheapSignal] = []
    for rank, point in enumerate(ordered, start=1):
        bp_residual = point["bp_residual"] if isinstance(point["bp_residual"], Decimal) else Decimal(str(point["bp_residual"]))
        price_residual = (
            point["price_residual"]
            if isinstance(point["price_residual"], Decimal)
            else Decimal(str(point["price_residual"]))
        )
        if bp_residual > threshold:
            classification = "CHEAP"
        elif bp_residual < -threshold:
            classification = "RICH"
        else:
            classification = "NEUTRAL"
        z_score = Decimal(0) if std == Decimal(0) else (bp_residual - mean) / std
        signals.append(
            RichCheapSignal(
                instrument_id=point["instrument_id"],
                rank=rank,
                classification=classification,
                cheapness_bps=bp_residual,
                price_residual=price_residual,
                bp_residual=bp_residual,
                z_score=z_score,
            )
        )
    return tuple(signals)


__all__ = ["RichCheapSignal", "rank_rich_cheap"]
