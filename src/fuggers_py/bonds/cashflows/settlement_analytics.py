"""Analytics settlement helpers.

The analytics layer keeps settlement conventions thin: the default calendar is
weekend-only, and the settlement status helper mirrors the bond-layer
ex-dividend semantics while remaining explicit about maturity handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from fuggers_py.bonds.cashflows.settlement import SettlementCalculator as _BondSettlementCalculator
from fuggers_py._core import CalendarId
from fuggers_py._core.ex_dividend import ExDividendRules
from fuggers_py._core.settlement_rules import SettlementRules
from fuggers_py._core.stub_rules import StubType
from fuggers_py._core.types import Date


class SettlementStatus(str, Enum):
    """Settlement status returned by analytics settlement checks."""

    NORMAL = "NORMAL"
    EX_DIVIDEND = "EX_DIVIDEND"
    AFTER_MATURITY = "AFTER_MATURITY"


@dataclass(frozen=True, slots=True)
class SettlementCalculator:
    """Wrapper around the bond-layer settlement calculator.

    Parameters
    ----------
    rules:
        Settlement rules to apply.
    calendar:
        Settlement calendar. Defaults to the weekend-only calendar.
    """

    rules: SettlementRules
    calendar: CalendarId = field(default_factory=CalendarId.weekend_only)

    def settlement_date(self, trade_date: Date) -> Date:
        """Return the settlement date for ``trade_date``."""

        return _BondSettlementCalculator(self.calendar, self.rules).settlement_date(trade_date)


def settlement_status(
    settlement_date: Date,
    next_coupon_date: Date | None,
    *,
    ex_dividend_rules: ExDividendRules | None = None,
) -> SettlementStatus:
    """Classify a settlement relative to the next coupon payment.

    Parameters
    ----------
    settlement_date:
        Proposed settlement date.
    next_coupon_date:
        Next coupon date, or ``None`` if the bond has matured.
    ex_dividend_rules:
        Optional ex-dividend rule set. When omitted or disabled, the status is
        ``NORMAL``.

    Returns
    -------
    SettlementStatus
        ``AFTER_MATURITY`` when no coupon remains, ``EX_DIVIDEND`` when the
        settlement date falls inside the ex-dividend window, otherwise
        ``NORMAL``.
    """

    if next_coupon_date is None:
        return SettlementStatus.AFTER_MATURITY
    if ex_dividend_rules is None or ex_dividend_rules.ex_dividend_days <= 0:
        return SettlementStatus.NORMAL
    ex_div_date = next_coupon_date.add_days(-int(ex_dividend_rules.ex_dividend_days))
    if settlement_date >= ex_div_date:
        return SettlementStatus.EX_DIVIDEND
    return SettlementStatus.NORMAL


__all__ = [
    "SettlementCalculator",
    "SettlementRules",
    "SettlementStatus",
    "StubType",
    "ExDividendRules",
    "settlement_status",
]
