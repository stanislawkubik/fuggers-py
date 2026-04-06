"""ETF basket analytics.

Basket helpers translate a portfolio into creation-unit quantities, clean and
dirty values, and per-share basket costs for ETF workflows.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from ..analytics import PortfolioAnalytics
from ..bucketing import bucket_by_sector
from ..portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class BasketAnalysis:
    """High-level ETF basket summary."""

    num_positions: int
    sector_counts: dict[str, int]
    total_quantity: Decimal

    @property
    def security_count(self) -> int:
        """Return the number of securities in the basket."""

        return self.num_positions


@dataclass(frozen=True, slots=True)
class BasketComponent:
    """One component in a creation basket."""

    name: str
    quantity: Decimal
    clean_price: Decimal | None
    dirty_price: Decimal | None
    market_value: Decimal
    dirty_value: Decimal
    accrued_interest: Decimal
    weight: Decimal
    sector: str | None = None


@dataclass(frozen=True, slots=True)
class BasketFlowSummary:
    """Creation-basket cash-flow summary in currency units."""

    component_count: int
    total_quantity: Decimal
    securities_market_value: Decimal
    securities_dirty_value: Decimal
    accrued_interest: Decimal
    cash_component: Decimal
    liabilities_component: Decimal
    total_basket_value: Decimal
    shares_outstanding: Decimal
    creation_unit_shares: Decimal

    @property
    def basket_per_share(self) -> Decimal:
        """Return the basket value per ETF share."""

        if self.creation_unit_shares == 0:
            return Decimal(0)
        return self.total_basket_value / self.creation_unit_shares


@dataclass(frozen=True, slots=True)
class CreationBasket(Sequence[BasketComponent]):
    """Ordered ETF creation basket and its flow summary."""

    components: tuple[BasketComponent, ...]
    flow_summary: BasketFlowSummary

    def __iter__(self) -> Iterator[BasketComponent]:
        return iter(self.components)

    def __len__(self) -> int:
        return len(self.components)

    def __getitem__(self, index: int | slice) -> BasketComponent | tuple[BasketComponent, ...]:
        return self.components[index]

    def by_name(self, name: str) -> BasketComponent | None:
        """Return the basket component with ``name`` if present."""

        return next((entry for entry in self.components if entry.name == name), None)

    @property
    def component_count(self) -> int:
        """Return the number of basket components."""

        return len(self.components)

    @property
    def basket_per_share(self) -> Decimal:
        """Return the basket value per ETF share."""

        return self.flow_summary.basket_per_share


def _validate_share_counts(shares_outstanding: Decimal, creation_unit_shares: Decimal) -> None:
    if shares_outstanding <= 0:
        raise ValueError("shares_outstanding must be positive.")
    if creation_unit_shares <= 0:
        raise ValueError("creation_unit_shares must be positive.")


def _position_name(position: object) -> str | None:
    if hasattr(position, "name"):
        return position.name()
    label = getattr(position, "label", None)
    return None if label is None else str(label)


def _sector_name(position: object | None) -> str | None:
    if position is None:
        return None
    sector_info = getattr(position, "sector_info", None)
    if sector_info is not None and getattr(sector_info, "sector", None) is not None:
        sector = sector_info.sector
        return getattr(sector, "value", str(sector))
    classification = getattr(position, "classification", None)
    if classification is not None and getattr(classification, "sector", None) is not None:
        sector = classification.sector
        return getattr(sector, "value", str(sector))
    return None


def build_creation_basket(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    shares_outstanding: Decimal,
    creation_unit_shares: Decimal = Decimal("50000"),
    liabilities: Decimal = Decimal(0),
) -> CreationBasket:
    """Build a creation basket scaled to the requested share count.

    The basket is scaled from the portfolio holdings to the requested ETF
    share count, and the flow summary reconciles securities, cash, and
    liabilities.
    """

    _validate_share_counts(shares_outstanding, creation_unit_shares)
    scale = creation_unit_shares / shares_outstanding
    analytics = PortfolioAnalytics(portfolio)
    try:
        metrics = analytics.position_metrics(curve, settlement_date)
    except ValueError as exc:
        raise ValueError("Creation basket construction requires prices or a valuation curve.") from exc

    originals = {
        name: position
        for position in portfolio.positions
        if (name := _position_name(position)) is not None
    }
    raw_components: list[BasketComponent] = []
    securities_market_value = Decimal(0)
    securities_dirty_value = Decimal(0)
    accrued_interest = Decimal(0)
    total_quantity = Decimal(0)

    for item in metrics:
        position = originals.get(item.name)
        quantity = getattr(position, "quantity", None)
        if quantity is None or quantity == 0:
            continue
        basket_quantity = quantity * scale
        market_value = item.clean_value * scale
        dirty_value = item.dirty_value * scale
        accrued_value = item.accrued_value * scale
        clean_price = item.clean_value / quantity
        dirty_price = item.dirty_value / quantity
        raw_components.append(
            BasketComponent(
                name=item.name,
                quantity=basket_quantity,
                clean_price=clean_price,
                dirty_price=dirty_price,
                market_value=market_value,
                dirty_value=dirty_value,
                accrued_interest=accrued_value,
                weight=Decimal(0),
                sector=_sector_name(position),
            )
        )
        total_quantity += basket_quantity
        securities_market_value += market_value
        securities_dirty_value += dirty_value
        accrued_interest += accrued_value

    dirty_base = securities_dirty_value if securities_dirty_value != 0 else Decimal(1)
    components = tuple(
        replace(component, weight=Decimal(0) if securities_dirty_value == 0 else component.dirty_value / dirty_base)
        for component in raw_components
    )
    cash_component = sum(
        (
            position.market_value()
            for position in portfolio.positions
            if hasattr(position, "market_value") and not hasattr(position, "quantity")
        ),
        Decimal(0),
    ) * scale
    liabilities_component = liabilities * scale
    total_basket_value = securities_dirty_value + cash_component - liabilities_component
    return CreationBasket(
        components=components,
        flow_summary=BasketFlowSummary(
            component_count=len(components),
            total_quantity=total_quantity,
            securities_market_value=securities_market_value,
            securities_dirty_value=securities_dirty_value,
            accrued_interest=accrued_interest,
            cash_component=cash_component,
            liabilities_component=liabilities_component,
            total_basket_value=total_basket_value,
            shares_outstanding=shares_outstanding,
            creation_unit_shares=creation_unit_shares,
        ),
    )


def analyze_etf_basket(portfolio: Portfolio) -> BasketAnalysis:
    """Return a high-level basket analysis for the portfolio."""

    sector_buckets = {key: len(value) for key, value in bucket_by_sector(portfolio).items()}
    return BasketAnalysis(
        num_positions=len(portfolio.positions),
        sector_counts=sector_buckets,
        total_quantity=portfolio.total_quantity(),
    )


__all__ = [
    "BasketAnalysis",
    "BasketComponent",
    "BasketFlowSummary",
    "CreationBasket",
    "analyze_etf_basket",
    "build_creation_basket",
]
