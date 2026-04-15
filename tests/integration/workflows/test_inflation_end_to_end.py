from __future__ import annotations

import json
from decimal import Decimal

from fuggers_py.core import Currency, Date, Price
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.market.snapshot import MarketDataSnapshot
from fuggers_py.market.sources import MarketDataProvider
from fuggers_py.calc import PricingRouter
from fuggers_py.market.curves.inflation import bootstrap_inflation_curve
from fuggers_py.measures.inflation import linker_swap_parity_check
from fuggers_py.pricers.rates import InflationSwapPricer
from fuggers_py.reference.inflation import (
    USD_CPI_U_NSA,
    load_monthly_cpi_fixings_csv,
    load_monthly_cpi_fixings_json,
    parse_treasury_auctioned_tips_json,
    treasury_cpi_source_from_fixings,
    tips_bond_from_treasury_auction_row,
)
from fuggers_py.products.rates import (
    PayReceive,
    StandardCouponInflationSwap,
    ZeroCouponInflationSwap,
)

from tests.helpers._rates_helpers import flat_curve


def test_inflation_end_to_end_from_treasury_adapter_to_routers(tmp_path) -> None:
    csv_path = tmp_path / "treasury_cpi.csv"
    csv_path.write_text(
        "\n".join(
            [
                "observation_month,cpi",
                "2023-10,100",
                "2023-11,100",
                "2024-04,104",
                "2024-05,104",
                "2024-10,108",
                "2024-11,108",
            ]
        )
    )
    json_path = tmp_path / "treasury_cpi.json"
    json_path.write_text(
        json.dumps(
            {
                "data": [
                    {"month": "2023-10", "reference_cpi": "100"},
                    {"month": "2023-11", "reference_cpi": "100"},
                    {"month": "2024-04", "reference_cpi": "104"},
                    {"month": "2024-05", "reference_cpi": "104"},
                    {"month": "2024-10", "reference_cpi": "108"},
                    {"month": "2024-11", "reference_cpi": "108"},
                ]
            }
        )
    )

    csv_fixings = load_monthly_cpi_fixings_csv(csv_path)
    json_fixings = load_monthly_cpi_fixings_json(json_path)

    assert csv_fixings == json_fixings

    fixing_source = treasury_cpi_source_from_fixings(csv_fixings)
    snapshot = MarketDataSnapshot(inflation_fixings=csv_fixings)
    provider = MarketDataProvider.from_snapshot(snapshot)

    tips = tips_bond_from_treasury_auction_row(
        parse_treasury_auctioned_tips_json(
            {
                "data": [
                    {
                        "CUSIP": "912810UH9",
                        "SecurityType": "Bond",
                        "SecurityTerm": "1-Year",
                        "SecurityTermWeekYear": "1-Year TIPS of January 2025",
                        "IssueDate": "2024-01-01T00:00:00",
                        "DatedDate": "2024-01-01T00:00:00",
                        "MaturityDate": "2025-01-01T00:00:00",
                        "InterestRate": "2.000000",
                        "RefCpiOnIssueDate": "100",
                        "RefCpiOnDatedDate": "100",
                    }
                ]
            }
        )[0]
    )
    tips_output = PricingRouter().price(
        tips,
        Date.from_ymd(2024, 7, 1),
        market_price=Price.new(Decimal("102.00"), Currency.USD),
        market_data=provider,
    )

    assert tips_output.pricing_path == "tips_real_yield"
    assert tips_output.yield_to_maturity is not None
    assert tips_output.dirty_price is not None

    discount_curve = flat_curve(Date.from_ymd(2024, 1, 10), "0.03")
    bootstrap = bootstrap_inflation_curve(
        [
            ZeroCouponInflationSwap.new(
                trade_date=Date.from_ymd(2024, 1, 10),
                effective_date=Date.from_ymd(2024, 1, 15),
                maturity_date=Date.from_ymd(2025, 1, 15),
                notional=Decimal("1000000"),
                fixed_rate=Decimal("0.0200"),
                pay_receive=PayReceive.PAY,
                currency=Currency.USD,
                inflation_convention=USD_CPI_U_NSA,
                instrument_id="ZCIS-CAL-1Y",
            ),
            ZeroCouponInflationSwap.new(
                trade_date=Date.from_ymd(2024, 1, 10),
                effective_date=Date.from_ymd(2024, 1, 15),
                maturity_date=Date.from_ymd(2026, 1, 15),
                notional=Decimal("1000000"),
                fixed_rate=Decimal("0.0350"),
                pay_receive=PayReceive.PAY,
                currency=Currency.USD,
                inflation_convention=USD_CPI_U_NSA,
                instrument_id="ZCIS-CAL-2Y",
            ),
        ],
        fixing_source=fixing_source,
        discount_curve=discount_curve,
    )
    curves = AnalyticsCurves(
        discount_curve=discount_curve,
        inflation_curve=bootstrap.curve,
        inflation_curves={"CPURNSA": bootstrap.curve},
    )
    zcis = ZeroCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        effective_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2025, 7, 15),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.0275"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        instrument_id="ZCIS-1",
    )
    scis = StandardCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        effective_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2025, 1, 15),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.0225"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        normalize_effective_date_to_reference_month_start=False,
        instrument_id="SCIS-1",
    )
    pricer = InflationSwapPricer()
    zcis_output = pricer.price(zcis, curves=curves)
    scis_output = pricer.price(scis, curves=curves)

    assert zcis_output.par_fixed_rate is not None
    assert scis_output.par_fixed_rate is not None

    parity = linker_swap_parity_check(
        nominal_yield=Decimal("0.0450"),
        real_yield=Decimal("0.0175"),
        inflation_swap_rate=scis_output.par_fixed_rate,
    )

    assert parity.linker_breakeven > Decimal(0)
    assert parity.swap_breakeven == scis_output.par_fixed_rate
