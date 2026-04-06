"""Settlement helpers (`fuggers_py.products.bonds.cashflows.settlement`).

The helper resolves settlement dates from a trade date, a calendar, and the
bond-settlement rules used by the reference layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.types import Date

from fuggers_py.reference.bonds.types import CalendarId, SettlementRules


@dataclass(frozen=True, slots=True)
class SettlementCalculator:
    """Resolve settlement dates from trade dates and bond settlement rules."""

    calendar: CalendarId
    rules: SettlementRules

    def settlement_date(self, trade_date: Date) -> Date:
        """Return the adjusted settlement date for ``trade_date``."""

        cal = self.calendar.to_calendar()
        return self.rules.settlement_date(trade_date, cal)


__all__ = ["SettlementCalculator"]
