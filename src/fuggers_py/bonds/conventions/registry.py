"""Convention registry and builder helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from fuggers_py._core import YieldCalculationRules
from .market import BondMarket
from .eurobond import eurobond_rules
from .german_bund import german_bund_rules
from .japanese_jgb import japanese_jgb_rules
from .uk_gilt import uk_gilt_rules
from .us_corporate import us_corporate_rules
from .us_treasury import us_treasury_rules


DEFAULT_REGISTRY: dict[BondMarket, YieldCalculationRules] = {
    BondMarket.US_TREASURY: us_treasury_rules(),
    BondMarket.US_CORPORATE: us_corporate_rules(),
    BondMarket.UK_GILT: uk_gilt_rules(),
    BondMarket.EUROBOND: eurobond_rules(),
    BondMarket.GERMAN_BUND: german_bund_rules(),
    BondMarket.JAPANESE_JGB: japanese_jgb_rules(),
}


@dataclass(frozen=True, slots=True)
class BondConventionRegistry:
    """Mapping from market identifiers to bundled yield-calculation rules."""

    rules_by_market: dict[BondMarket, YieldCalculationRules]

    @classmethod
    def default(cls) -> "BondConventionRegistry":
        """Return the library's default market-convention registry."""

        return cls(rules_by_market=dict(DEFAULT_REGISTRY))

    def lookup(self, market: BondMarket) -> YieldCalculationRules:
        """Return rules for ``market``."""

        return self.rules_by_market[market]


@dataclass(slots=True)
class BondConventionsBuilder:
    """Builder for resolving a convention preset from a registry."""

    market: BondMarket | None = None
    registry: BondConventionRegistry = field(default_factory=BondConventionRegistry.default)

    def with_market(self, market: BondMarket) -> "BondConventionsBuilder":
        """Select the market preset to build."""

        self.market = market
        return self

    def build(self) -> YieldCalculationRules:
        """Return the rules for the configured market."""

        if self.market is None:
            raise ValueError("BondConventionsBuilder requires a market.")
        return self.registry.lookup(self.market)


__all__ = ["BondConventionRegistry", "BondConventionsBuilder", "DEFAULT_REGISTRY"]
