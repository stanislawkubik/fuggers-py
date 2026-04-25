"""Full asset-swap product definitions.

Asset-swap quotes use percent-of-par bond prices together with raw-decimal
spreads. Exactly one of ``market_clean_price`` or ``market_dirty_price`` must
be supplied, and the floating-leg notional can either stay at par or be scaled
off the bond proceeds depending on the asset-swap type.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.bonds.instruments import FixedBond
from fuggers_py.bonds.types import ASWType
from fuggers_py._core.types import Date
from fuggers_py._core.ids import InstrumentId

from .common import FloatingLegSpec


def _to_decimal(value: object | None) -> Decimal | None:
    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class AssetSwap:
    """Asset swap around a fixed-rate bond.

    Attributes
    ----------
    bond:
        Fixed-rate bond being swapped into floating-rate exposure.
    settlement_date:
        Valuation settlement date used for accrued interest and dirty price.
    floating_leg:
        Floating leg that replaces the bond coupon stream.
    quoted_spread:
        Quoted spread as a raw decimal.
    market_clean_price, market_dirty_price:
        Exactly one market price input in percent of par.
    asset_swap_type:
        Asset-swap flavor controlling how the floating notional is scaled.

    Notes
    -----
    ``quoted_spread`` and the funding-rate fields are raw decimals. The market
    price inputs are quoted in percent of par.
    """

    bond: FixedBond
    settlement_date: Date
    floating_leg: FloatingLegSpec
    quoted_spread: Decimal = Decimal(0)
    asset_swap_type: ASWType = ASWType.PAR_PAR
    market_clean_price: Decimal | None = None
    market_dirty_price: Decimal | None = None
    repo_rate: Decimal | None = None
    general_collateral_rate: Decimal | None = None
    unsecured_overnight_rate: Decimal | None = None
    term_rate: Decimal | None = None
    compounding_convexity_adjustment: Decimal = Decimal(0)
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "quoted_spread", _to_decimal(self.quoted_spread))
        if self.market_clean_price is not None:
            object.__setattr__(self, "market_clean_price", _to_decimal(self.market_clean_price))
        if self.market_dirty_price is not None:
            object.__setattr__(self, "market_dirty_price", _to_decimal(self.market_dirty_price))
        if self.repo_rate is not None:
            object.__setattr__(self, "repo_rate", _to_decimal(self.repo_rate))
        if self.general_collateral_rate is not None:
            object.__setattr__(self, "general_collateral_rate", _to_decimal(self.general_collateral_rate))
        if self.unsecured_overnight_rate is not None:
            object.__setattr__(self, "unsecured_overnight_rate", _to_decimal(self.unsecured_overnight_rate))
        if self.term_rate is not None:
            object.__setattr__(self, "term_rate", _to_decimal(self.term_rate))
        object.__setattr__(
            self,
            "compounding_convexity_adjustment",
            _to_decimal(self.compounding_convexity_adjustment),
        )
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.bond.maturity_date() <= self.settlement_date:
            raise ValueError("AssetSwap requires settlement before bond maturity.")
        if self.floating_leg.currency is not self.bond.currency():
            raise ValueError("AssetSwap requires bond and floating leg in the same currency.")
        has_clean = self.market_clean_price is not None
        has_dirty = self.market_dirty_price is not None
        if has_clean == has_dirty:
            raise ValueError("AssetSwap requires exactly one of market_clean_price or market_dirty_price.")

    def currency(self):
        """Return the bond currency."""

        return self.bond.currency()

    def maturity_date(self) -> Date:
        """Return the bond maturity date."""

        return self.bond.maturity_date()

    def accrued_interest(self) -> Decimal:
        """Return accrued interest at the settlement date."""

        return self.bond.accrued_interest(self.settlement_date)

    def dirty_price(self) -> Decimal:
        """Return the market dirty price in percent of par."""

        if self.market_dirty_price is not None:
            return self.market_dirty_price
        assert self.market_clean_price is not None
        return self.market_clean_price + self.accrued_interest()

    def clean_price(self) -> Decimal:
        """Return the market clean price in percent of par."""

        if self.market_clean_price is not None:
            return self.market_clean_price
        assert self.market_dirty_price is not None
        return self.market_dirty_price - self.accrued_interest()

    def effective_floating_notional(self) -> Decimal:
        """Return the floating-leg notional used in PV calculations."""

        if self.asset_swap_type is ASWType.PROCEEDS:
            return self.floating_leg.notional * self.dirty_price() / Decimal(100)
        return self.floating_leg.notional


__all__ = ["AssetSwap"]
