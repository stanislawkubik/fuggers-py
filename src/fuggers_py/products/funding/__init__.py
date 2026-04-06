"""Funding product definitions.

The funding package currently exposes repo trade objects and their associated
cash and collateral conventions.
"""

from __future__ import annotations

from .repo import RepoTrade

__all__ = ["RepoTrade"]
