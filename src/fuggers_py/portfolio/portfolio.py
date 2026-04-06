"""Portfolio container types.

This module defines the immutable portfolio container and the small builder
used to assemble it. The portfolio is currency-denominated and may hold both
bond positions and cash positions. Portfolio-level helpers keep quantity,
clean-value, dirty-value, and cash semantics separate so analytics can
aggregate correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py.core.types import Currency

from .types import CashPosition, Holding, Position


@dataclass(frozen=True, slots=True)
class Portfolio:
    """A currency-denominated collection of positions and cash.

    Attributes
    ----------
    positions:
        The portfolio holdings, stored in input order.
    currency:
        Base reporting currency for portfolio-level analytics.
    """

    positions: tuple[Position | CashPosition, ...]
    currency: Currency

    @classmethod
    def new(cls, positions: list[Position | CashPosition], currency: Currency) -> "Portfolio":
        """Build a portfolio from a mutable position list.

        The input list is converted to an immutable tuple so later analytics
        see a stable position order.
        """

        return cls(positions=tuple(positions), currency=currency)

    def total_quantity(self) -> Decimal:
        """Return the sum of quantity-bearing position quantities.

        Cash positions are ignored because they do not carry a par quantity.
        """

        return sum((position.quantity for position in self.positions if hasattr(position, "quantity")), Decimal(0))

    def holdings(self) -> tuple[Position | CashPosition, ...]:
        """Return the raw holdings tuple, including cash positions."""

        return self.positions

    def investable_holdings(self) -> tuple[Holding, ...]:
        """Return the bond holdings, excluding cash positions."""

        return tuple(position for position in self.positions if isinstance(position, Holding))

    def cash_positions(self) -> tuple[CashPosition, ...]:
        """Return the cash positions in the portfolio."""

        return tuple(position for position in self.positions if isinstance(position, CashPosition))

    def total_market_value(self) -> Decimal:
        """Return total market value in the portfolio's base currency units.

        Bond holdings contribute clean market value while cash contributes its
        face amount. The result is therefore a clean, portfolio-level value
        proxy rather than a dirty PV.
        """

        total = Decimal(0)
        for position in self.positions:
            if isinstance(position, CashPosition):
                total += position.market_value()
            elif isinstance(position, Holding):
                total += position.market_value_amount
        return total


@dataclass(slots=True)
class PortfolioBuilder:
    """Incrementally assemble a :class:`Portfolio`."""

    currency: Currency | None = None
    _positions: list[Position | CashPosition] = field(default_factory=list)

    def with_currency(self, currency: Currency) -> "PortfolioBuilder":
        """Set the portfolio reporting currency."""

        self.currency = currency
        return self

    def add_position(self, position: Position | CashPosition) -> "PortfolioBuilder":
        """Append a position and infer currency from it if needed.

        If the builder does not yet have a currency, it adopts the position's
        currency on the first appended item.
        """

        self._positions.append(position)
        if self.currency is None:
            currency = getattr(position, "currency", None)
            self.currency = currency() if callable(currency) else currency
        return self

    def add_holding(self, holding: Position | CashPosition) -> "PortfolioBuilder":
        """Compatibility alias for :meth:`add_position`."""

        return self.add_position(holding)

    def add_positions(self, positions: list[Position | CashPosition]) -> "PortfolioBuilder":
        """Append multiple positions to the builder."""

        for position in positions:
            self.add_position(position)
        return self

    def build(self) -> Portfolio:
        """Create the immutable portfolio.

        Raises
        ------
        ValueError
            If no currency has been set or inferred.
        """

        if self.currency is None:
            raise ValueError("PortfolioBuilder requires a currency.")
        return Portfolio.new(self._positions, currency=self.currency)


__all__ = ["Portfolio", "PortfolioBuilder"]
