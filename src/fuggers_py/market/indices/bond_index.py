"""Bond index definitions with fixing support.

The bond-index layer bridges named reference rates, stored fixings, and the
overnight or forward-rate conventions needed by floating-rate products.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py.reference.bonds.types import RateIndex
from fuggers_py.core.types import Currency, Date

from .conventions import IndexConventions
from .fixing_store import IndexFixingStore, IndexSource


@dataclass(frozen=True, slots=True)
class BondIndex:
    """Reference-rate definition backed by an optional fixing store.

    The object names an index, carries its market conventions, and resolves the
    relevant fixing or fallback rate when a coupon period needs one.
    """

    name: str
    rate_index: RateIndex | None = None
    currency: Currency | None = None
    source: IndexSource = IndexSource.MANUAL
    conventions: IndexConventions = field(default_factory=IndexConventions)
    fixing_store: IndexFixingStore | None = None

    def fixing(self, fixing_date: Date, *, store: IndexFixingStore | None = None) -> Decimal | None:
        """Return the stored fixing for ``fixing_date`` when available."""

        active_store = store or self.fixing_store
        if active_store is None:
            return None
        return active_store.get_rate(self.name, fixing_date)

    def rate_for_period(
        self,
        start_date: Date,
        end_date: Date,
        *,
        store: IndexFixingStore | None = None,
        fallback_rate: Decimal | None = None,
        forward_curve: object | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Return the rate applied to an accrual period.

        The rate is resolved from fixings when possible and can fall back to a
        supplied flat rate or forward curve depending on the active
        conventions.
        """

        active_store = store or self.fixing_store
        if active_store is None:
            if fallback_rate is None:
                raise KeyError(f"No fixing store configured for index {self.name}.")
            return fallback_rate
        return active_store.rate_for_period(
            self.name,
            start_date,
            end_date,
            conventions=self.conventions,
            fallback_rate=fallback_rate,
            calendar=None,
            forward_curve=forward_curve,
            as_of=as_of,
        )

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


__all__ = ["BondIndex"]
