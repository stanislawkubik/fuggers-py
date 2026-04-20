from __future__ import annotations

from decimal import Decimal

from fuggers_py._products.bonds import TipsBond
from fuggers_py._core import YieldCalculationRules
from fuggers_py._products.bonds.traits import CashFlowType
from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._core import YearMonth
from fuggers_py._market.snapshot import InflationFixing
from fuggers_py._market.sources import InMemoryInflationFixingSource
from fuggers_py.inflation import USD_CPI_U_NSA


def _fixing(month: str, value: str) -> InflationFixing:
    return InflationFixing(
        index_name="CPURNSA",
        observation_month=YearMonth.parse(month),
        value=Decimal(value),
    )


def _base_fixing_source() -> InMemoryInflationFixingSource:
    return InMemoryInflationFixingSource(
        [
            _fixing("2023-10", "100"),
            _fixing("2023-11", "100"),
            _fixing("2024-04", "104"),
            _fixing("2024-05", "104"),
            _fixing("2024-10", "108"),
            _fixing("2024-11", "108"),
            _fixing("2025-04", "112"),
            _fixing("2025-05", "112"),
            _fixing("2025-10", "116"),
            _fixing("2025-11", "116"),
        ]
    )


def test_tips_schedule_generation_and_coupon_cashflow_count() -> None:
    source = _base_fixing_source()
    bond = TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2026, 1, 15),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        dated_date=Date.from_ymd(2024, 1, 15),
        base_reference_date=Date.from_ymd(2024, 1, 15),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
        rules=YieldCalculationRules.us_treasury(),
        fixing_source=source,
    )

    flows = bond.cash_flows()
    coupon_flows = [flow for flow in flows if flow.flow_type is CashFlowType.INFLATION_COUPON]

    assert len(bond.schedule().dates) == 5
    assert len(coupon_flows) == 4


def test_tips_index_ratio_is_positive() -> None:
    source = _base_fixing_source()
    bond = TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 1),
        maturity_date=Date.from_ymd(2025, 1, 1),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        dated_date=Date.from_ymd(2024, 1, 1),
        base_reference_date=Date.from_ymd(2024, 1, 1),
        fixing_source=source,
    )

    assert bond.index_ratio(Date.from_ymd(2024, 7, 1)) > Decimal(0)


def test_tips_final_redemption_uses_adjusted_principal_when_above_par() -> None:
    source = _base_fixing_source()
    bond = TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 1),
        maturity_date=Date.from_ymd(2025, 1, 1),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        dated_date=Date.from_ymd(2024, 1, 1),
        base_reference_date=Date.from_ymd(2024, 1, 1),
        fixing_source=source,
    )

    assert bond.final_principal_redemption() == Decimal("108")


def test_tips_final_redemption_is_floored_at_par_under_deflation() -> None:
    source = InMemoryInflationFixingSource(
        [
            _fixing("2023-10", "100"),
            _fixing("2023-11", "100"),
            _fixing("2024-04", "96"),
            _fixing("2024-05", "96"),
            _fixing("2024-10", "90"),
            _fixing("2024-11", "90"),
        ]
    )
    bond = TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 1),
        maturity_date=Date.from_ymd(2025, 1, 1),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        dated_date=Date.from_ymd(2024, 1, 1),
        base_reference_date=Date.from_ymd(2024, 1, 1),
        fixing_source=source,
    )

    assert bond.adjusted_principal(Date.from_ymd(2025, 1, 1)) == Decimal("90")
    assert bond.final_principal_redemption() == Decimal("100")


def test_tips_coupon_amount_uses_index_ratio_and_original_principal() -> None:
    source = InMemoryInflationFixingSource(
        [
            _fixing("2023-10", "100"),
            _fixing("2023-11", "100"),
            _fixing("2024-04", "104"),
            _fixing("2024-05", "104"),
            _fixing("2024-10", "104"),
            _fixing("2024-11", "104"),
        ]
    )
    bond = TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 1),
        maturity_date=Date.from_ymd(2025, 1, 1),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        dated_date=Date.from_ymd(2024, 1, 1),
        base_reference_date=Date.from_ymd(2024, 1, 1),
        fixing_source=source,
    )

    first_coupon = bond.projected_coupon_cash_flows()[0]

    assert first_coupon.flow_type is CashFlowType.INFLATION_COUPON
    assert first_coupon.amount == Decimal("1.00")
    assert first_coupon.factor == Decimal("1.04")
    assert first_coupon.factored_amount() == Decimal("1.0400")


def test_tips_cash_flow_schedule_uses_core_inflation_cashflow_helpers() -> None:
    source = _base_fixing_source()
    bond = TipsBond.new(
        issue_date=Date.from_ymd(2024, 1, 1),
        maturity_date=Date.from_ymd(2025, 1, 1),
        coupon_rate=Decimal("0.02"),
        inflation_convention=USD_CPI_U_NSA,
        dated_date=Date.from_ymd(2024, 1, 1),
        base_reference_date=Date.from_ymd(2024, 1, 1),
        fixing_source=source,
    )

    schedule = bond.cash_flow_schedule()
    final_flow = list(schedule)[-1]

    assert list(schedule)[0].is_inflation_linked() is True
    assert final_flow.is_inflation_linked() is True
    assert final_flow.amount() == Decimal("108")
