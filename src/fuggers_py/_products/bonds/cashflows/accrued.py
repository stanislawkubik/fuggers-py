"""Accrued interest calculations (`fuggers_py._products.bonds.cashflows.accrued`).

The helper routines translate a bond's schedule, day-count convention, and
accrued-interest rule into a currency amount for a given settlement date.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core.daycounts import ActActIcma
from fuggers_py._core.types import Date, Frequency

from fuggers_py._core.errors import InvalidBondSpec
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core.yield_convention import AccruedConvention


@dataclass(frozen=True, slots=True)
class AccruedInterestInputs:
    """Inputs for coupon accrual calculations.

    Parameters
    ----------
    settlement_date
        Settlement date at which accrued interest is measured.
    accrual_start, accrual_end
        Unadjusted coupon-accrual bounds for the active coupon period.
    coupon_amount
        Coupon cash amount earned over the active accrual period.
    coupon_date
        Adjusted payment date for the coupon period.
    full_coupon_amount
        Full coupon amount used by ex-dividend logic when the next coupon is
        economically detached from the bond.
    period_start, period_end
        Optional reference-period bounds used by ICMA-style stub accrual.
    """

    settlement_date: Date
    accrual_start: Date
    accrual_end: Date
    coupon_amount: Decimal
    coupon_date: Date
    full_coupon_amount: Decimal
    period_start: Date | None = None
    period_end: Date | None = None


class AccruedInterestCalculator:
    """Accrued-interest routines for standard and irregular coupon periods."""

    @staticmethod
    def _validate_inputs(inputs: AccruedInterestInputs) -> None:
        if inputs.accrual_end <= inputs.accrual_start:
            raise InvalidBondSpec(reason="Accrued interest requires accrual_end to be after accrual_start.")
        if inputs.coupon_date < inputs.accrual_end:
            raise InvalidBondSpec(reason="coupon_date must not precede accrual_end.")

    @staticmethod
    def _shift_reference_date(date: Date, months: int, *, preserve_eom: bool) -> Date:
        shifted = date.add_months(months)
        if preserve_eom:
            return shifted.end_of_month()
        return shifted

    @staticmethod
    def _icma_year_fraction(
        start: Date,
        end: Date,
        *,
        day_count: ActActIcma,
        period_start: Date,
        period_end: Date,
        frequency: Frequency,
    ) -> Decimal:
        if end <= start:
            return Decimal(0)
        if period_end <= period_start:
            raise InvalidBondSpec(reason="ICMA accrued calculations require period_start < period_end.")

        months = frequency.months_per_period()
        if months <= 0:
            return day_count.year_fraction_with_period(start, end, period_start, period_end)

        preserve_eom = period_start.is_end_of_month() or period_end.is_end_of_month()
        boundaries: list[Date] = [period_start, period_end]

        while start < boundaries[0]:
            boundaries.insert(
                0,
                AccruedInterestCalculator._shift_reference_date(
                    boundaries[0],
                    -months,
                    preserve_eom=preserve_eom,
                ),
            )

        while end > boundaries[-1]:
            boundaries.append(
                AccruedInterestCalculator._shift_reference_date(
                    boundaries[-1],
                    months,
                    preserve_eom=preserve_eom,
                ),
            )

        total = Decimal(0)
        for i in range(1, len(boundaries)):
            segment_start = boundaries[i - 1]
            segment_end = boundaries[i]
            overlap_start = Date.max(start, segment_start)
            overlap_end = Date.min(end, segment_end)
            if overlap_end <= overlap_start:
                continue
            total += day_count.year_fraction_with_period(
                overlap_start,
                overlap_end,
                segment_start,
                segment_end,
            )
        return total

    @staticmethod
    def _year_fraction(
        start: Date,
        end: Date,
        *,
        inputs: AccruedInterestInputs,
        rules: YieldCalculationRules,
    ) -> Decimal:
        if end <= start:
            return Decimal(0)
        day_count = rules.accrual_day_count_obj()
        if (
            isinstance(day_count, ActActIcma)
            and inputs.period_start is not None
            and inputs.period_end is not None
        ):
            return AccruedInterestCalculator._icma_year_fraction(
                start,
                end,
                day_count=day_count,
                period_start=inputs.period_start,
                period_end=inputs.period_end,
                frequency=rules.frequency,
            )
        return day_count.year_fraction(start, end)

    @staticmethod
    def _coupon_fraction(inputs: AccruedInterestInputs, *, rules: YieldCalculationRules) -> Decimal:
        period_fraction = AccruedInterestCalculator._year_fraction(
            inputs.accrual_start,
            inputs.accrual_end,
            inputs=inputs,
            rules=rules,
        )
        if period_fraction == 0:
            return Decimal(0)
        elapsed_fraction = AccruedInterestCalculator._year_fraction(
            inputs.accrual_start,
            inputs.settlement_date,
            inputs=inputs,
            rules=rules,
        )
        return elapsed_fraction / period_fraction

    @staticmethod
    def standard(inputs: AccruedInterestInputs, *, rules: YieldCalculationRules) -> Decimal:
        """Return accrued interest for the supplied bond rules.

        Parameters
        ----------
        inputs
            Coupon-period inputs for the settlement being priced.
        rules
            Yield and accrual rules that define the day-count basis and accrued
            interest convention.

        Returns
        -------
        Decimal
            Accrued coupon amount in currency units, not percent-of-par.
        """

        AccruedInterestCalculator._validate_inputs(inputs)
        if inputs.settlement_date <= inputs.accrual_start:
            return Decimal(0)
        if inputs.settlement_date >= inputs.accrual_end:
            return Decimal(0)

        if rules.accrued_convention is AccruedConvention.NONE:
            return Decimal(0)

        if rules.accrued_convention in {
            AccruedConvention.STANDARD,
            AccruedConvention.EX_DIVIDEND,
            AccruedConvention.RECORD_DATE,
            AccruedConvention.CUM_DIVIDEND,
        }:
            return inputs.coupon_amount * AccruedInterestCalculator._coupon_fraction(inputs, rules=rules)

        if rules.accrued_convention is AccruedConvention.USING_YEAR_FRACTION:
            return inputs.coupon_amount * AccruedInterestCalculator._coupon_fraction(inputs, rules=rules)

        if rules.accrued_convention is AccruedConvention.ISMA:
            return AccruedInterestCalculator.irregular_period(inputs, rules=rules)

        return Decimal(0)

    @staticmethod
    def ex_dividend(inputs: AccruedInterestInputs, *, rules: YieldCalculationRules) -> Decimal:
        """Return accrued interest after applying ex-dividend detachment rules."""

        standard = AccruedInterestCalculator.standard(inputs, rules=rules)
        ex_rules = rules.ex_dividend_rules
        if ex_rules is None or ex_rules.ex_dividend_days <= 0:
            return standard

        calendar = rules.calendar.to_calendar()
        ex_dividend_date = calendar.add_business_days(inputs.coupon_date, -int(ex_rules.ex_dividend_days))
        if ex_dividend_date <= inputs.settlement_date < inputs.coupon_date:
            return standard - inputs.full_coupon_amount
        return standard

    @staticmethod
    def irregular_period(inputs: AccruedInterestInputs, *, rules: YieldCalculationRules) -> Decimal:
        """Return accrued interest for stub periods using the active rules."""

        AccruedInterestCalculator._validate_inputs(inputs)
        if inputs.settlement_date <= inputs.accrual_start:
            return Decimal(0)
        if inputs.settlement_date >= inputs.accrual_end:
            return Decimal(0)
        return inputs.coupon_amount * AccruedInterestCalculator._coupon_fraction(inputs, rules=rules)


__all__ = ["AccruedInterestInputs", "AccruedInterestCalculator"]
