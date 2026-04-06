"""Optional deterministic jump-diffusion curve overlays.

This module does not estimate a stochastic model. Instead it applies a
transparent, externally-parameterized convexity / jump overlay to an existing
curve so research workflows can experiment with alternative curve views
without touching the default production path.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import exp

from .short_rate_base import ShortRateModelCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class JumpDiffusionAdjustment:
    """Decomposition of the jump-diffusion adjustment at a tenor.

    The record separates the diffusion, jump, and risk-premium pieces so the
    adjusted zero rate can be audited component by component.
    """

    tenor_years: Decimal
    diffusion_adjustment: Decimal
    jump_adjustment: Decimal
    risk_premium_adjustment: Decimal
    total_adjustment: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenor_years", _to_decimal(self.tenor_years))
        object.__setattr__(self, "diffusion_adjustment", _to_decimal(self.diffusion_adjustment))
        object.__setattr__(self, "jump_adjustment", _to_decimal(self.jump_adjustment))
        object.__setattr__(self, "risk_premium_adjustment", _to_decimal(self.risk_premium_adjustment))
        object.__setattr__(self, "total_adjustment", _to_decimal(self.total_adjustment))


@dataclass(frozen=True, slots=True)
class JumpDiffusionCurve(ShortRateModelCurve):
    """Deterministic jump-diffusion inspired overlay.

    The adjusted annualized zero rate is

    ``z_adj(t) = z_base(t) + 0.5 * sigma^2 * t + lambda * (E[e^J] - 1) + k``

    where ``J ~ N(mean_jump_size, jump_volatility^2)`` and ``k`` is an
    optional additive risk-premium term. This keeps the formula explicit and
    externally parameterized.
    """

    diffusion_volatility: Decimal = Decimal(0)
    jump_intensity: Decimal = Decimal(0)
    mean_jump_size: Decimal = Decimal(0)
    jump_volatility: Decimal = Decimal(0)
    risk_premium_adjustment: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        object.__setattr__(self, "diffusion_volatility", _to_decimal(self.diffusion_volatility))
        object.__setattr__(self, "jump_intensity", _to_decimal(self.jump_intensity))
        object.__setattr__(self, "mean_jump_size", _to_decimal(self.mean_jump_size))
        object.__setattr__(self, "jump_volatility", _to_decimal(self.jump_volatility))
        object.__setattr__(self, "risk_premium_adjustment", _to_decimal(self.risk_premium_adjustment))
        if self.diffusion_volatility < Decimal(0):
            raise ValueError("JumpDiffusionCurve diffusion_volatility must be non-negative.")
        if self.jump_intensity < Decimal(0):
            raise ValueError("JumpDiffusionCurve jump_intensity must be non-negative.")
        if self.jump_volatility < Decimal(0):
            raise ValueError("JumpDiffusionCurve jump_volatility must be non-negative.")

    def diffusion_adjustment_at_tenor(self, tenor_years: object) -> Decimal:
        """Return the diffusion convexity adjustment at a tenor."""
        tenor = _to_decimal(tenor_years)
        if tenor <= Decimal(0):
            return Decimal(0)
        sigma = self.diffusion_volatility
        return Decimal("0.5") * sigma * sigma * tenor

    def jump_adjustment(self) -> Decimal:
        """Return the tenor-independent jump adjustment term."""
        jump_multiplier = exp(float(self.mean_jump_size + (Decimal("0.5") * self.jump_volatility * self.jump_volatility))) - 1.0
        return self.jump_intensity * Decimal(str(jump_multiplier))

    def adjustment_components(self, tenor_years: object) -> JumpDiffusionAdjustment:
        """Return the diffusion, jump, and risk-premium components."""
        tenor = _to_decimal(tenor_years)
        diffusion = self.diffusion_adjustment_at_tenor(tenor)
        jump = self.jump_adjustment()
        total = diffusion + jump + self.risk_premium_adjustment
        return JumpDiffusionAdjustment(
            tenor_years=tenor,
            diffusion_adjustment=diffusion,
            jump_adjustment=jump,
            risk_premium_adjustment=self.risk_premium_adjustment,
            total_adjustment=total,
        )

    def adjusted_zero_rate_at_tenor(self, tenor_years: object) -> Decimal:
        """Return the base zero rate plus the deterministic adjustments."""
        tenor = _to_decimal(tenor_years)
        base_zero = self.base_zero_rate_at_tenor(tenor)
        return base_zero + self.adjustment_components(tenor).total_adjustment


__all__ = ["JumpDiffusionAdjustment", "JumpDiffusionCurve"]
