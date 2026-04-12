"""Funding-specific calc-layer pricing router.

The funding router stays separate from the bond router because repo trades use
raw decimal funding rates, currency cash amounts, and collateral valuation
instead of bond clean-price conventions.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.calc.output import RepoPricingResult
from fuggers_py.market.curve_support import forward_rate_between_dates, zero_rate_at_date
from fuggers_py.market.curves import DiscountingCurve
from fuggers_py.products.funding import RepoTrade


@dataclass(frozen=True, slots=True)
class FundingPricingRouter:
    """Price repo trades against an optional repo curve."""

    def price_repo(self, trade: RepoTrade, *, repo_curve: DiscountingCurve | None = None) -> RepoPricingResult:
        """Price a repo trade and report carry and spread diagnostics.

        The funding spread is reported as ``trade.rate - curve_zero_rate`` so a
        positive spread indicates the trade funds above the curve. When no repo
        curve is supplied, the curve-derived fields are left unset.
        """
        zero_rate = None if repo_curve is None else zero_rate_at_date(repo_curve, trade.end_date)
        forward_rate = None if repo_curve is None else forward_rate_between_dates(repo_curve, trade.start_date, trade.end_date)
        return RepoPricingResult(
            collateral_value=trade.collateral_market_value(),
            haircut_amount=trade.haircut_amount(),
            cash_lent=trade.cash_lent(),
            year_fraction=trade.year_fraction(),
            interest_amount=trade.interest_amount(),
            repurchase_amount=trade.repurchase_amount(),
            curve_zero_rate=zero_rate,
            forward_rate=forward_rate,
            funding_spread=None if zero_rate is None else trade.rate - zero_rate,
        )

    def price_batch(
        self,
        trades: list[RepoTrade] | tuple[RepoTrade, ...],
        *,
        repo_curve: DiscountingCurve | None = None,
    ) -> tuple[RepoPricingResult, ...]:
        """Price a batch of repo trades against the same curve input."""
        return tuple(self.price_repo(trade, repo_curve=repo_curve) for trade in trades)


__all__ = ["FundingPricingRouter", "RepoPricingResult"]
