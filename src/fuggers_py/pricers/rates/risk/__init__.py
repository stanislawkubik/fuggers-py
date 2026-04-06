"""Rates first-order risk helpers and key-rate algorithms.

This namespace exposes the public rates risk helpers used by swap, FRA, and
basis-swap pricers. ``dv01`` is the canonical name for the parallel 1 bp PV
change. ``pv01`` and ``bpv`` remain compatibility aliases where callers still
expect them. The key-rate helpers split that same first-order risk into
tenor-specific buckets.
"""

from __future__ import annotations

from .bpv import (
    basis_swap_dv01,
    basis_swap_pv01,
    bpv,
    dv01,
    fra_dv01,
    fra_pv01,
    pv01,
    swap_dv01,
    swap_pv01,
)
from .key_rate import basis_swap_key_rate_risk, fra_key_rate_risk, key_rate_risk, swap_key_rate_risk

__all__ = [
    "basis_swap_key_rate_risk",
    "basis_swap_dv01",
    "basis_swap_pv01",
    "bpv",
    "dv01",
    "fra_key_rate_risk",
    "fra_dv01",
    "fra_pv01",
    "key_rate_risk",
    "pv01",
    "swap_key_rate_risk",
    "swap_dv01",
    "swap_pv01",
]
