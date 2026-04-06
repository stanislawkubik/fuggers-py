"""Optional advanced curve-model overlays.

These research overlays sit on top of a base :class:`~fuggers_py.core.traits.YieldCurve`
and preserve the same zero-rate and discount-factor interface. They are
intended for alternative curve views such as shadow-rate floors and
deterministic jump-diffusion adjustments, not for the standard bootstrap path.
"""

from __future__ import annotations

from .jump_diffusion import JumpDiffusionAdjustment, JumpDiffusionCurve
from .shadow_rate import ShadowRateCurve
from .short_rate_base import ShortRateModelCurve, ShortRateModelPoint

__all__ = [
    "JumpDiffusionAdjustment",
    "JumpDiffusionCurve",
    "ShadowRateCurve",
    "ShortRateModelCurve",
    "ShortRateModelPoint",
]
