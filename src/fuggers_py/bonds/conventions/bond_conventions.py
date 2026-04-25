"""Bond market conventions (`fuggers_py.bonds.conventions.bond_conventions`).

This module is a lightweight wrapper around `YieldCalculationRules` presets.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py._core import YieldCalculationRules
from .market import BondMarket
from .registry import BondConventionRegistry


@dataclass(frozen=True, slots=True)
class BondConventions:
    """Named market conventions paired with concrete yield-calculation rules."""

    rules: YieldCalculationRules
    market: BondMarket | None = None

    _registry = BondConventionRegistry.default()

    @classmethod
    def us_treasury(cls) -> "BondConventions":
        """Return the bundled US Treasury market convention preset."""

        return cls(rules=YieldCalculationRules.us_treasury(), market=BondMarket.US_TREASURY)

    @classmethod
    def us_corporate(cls) -> "BondConventions":
        """Return the bundled US corporate bond convention preset."""

        return cls(rules=YieldCalculationRules.us_corporate(), market=BondMarket.US_CORPORATE)

    @classmethod
    def uk_gilt(cls) -> "BondConventions":
        """Return the bundled UK gilt convention preset."""

        return cls(rules=YieldCalculationRules.uk_gilt(), market=BondMarket.UK_GILT)

    @classmethod
    def eurobond(cls) -> "BondConventions":
        """Return the bundled Eurobond convention preset."""

        return cls(rules=YieldCalculationRules.eurobond(), market=BondMarket.EUROBOND)

    @classmethod
    def german_bund(cls) -> "BondConventions":
        """Return the bundled German Bund convention preset."""

        return cls(rules=YieldCalculationRules.german_bund(), market=BondMarket.GERMAN_BUND)

    @classmethod
    def japanese_jgb(cls) -> "BondConventions":
        """Return the bundled Japanese government bond convention preset."""

        return cls(rules=YieldCalculationRules.japanese_jgb(), market=BondMarket.JAPANESE_JGB)

    @classmethod
    def for_market(cls, market: BondMarket) -> "BondConventions":
        """Return conventions resolved from the default registry."""

        return cls(rules=cls._registry.lookup(market), market=market)


__all__ = ["BondConventions"]
