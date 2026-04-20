"""Value-at-risk helpers (`fuggers_py._measures.risk.var`).

VaR helpers return raw decimal loss magnitudes together with the confidence
level and calculation method used.
"""

from __future__ import annotations

from .historical import historical_var
from .parametric import parametric_var, parametric_var_from_dv01
from .types import VaRMethod, VaRResult

__all__ = [
    "historical_var",
    "parametric_var",
    "parametric_var_from_dv01",
    "VaRMethod",
    "VaRResult",
]
