from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Date
from fuggers_py.calc import (
    AnalyticsPublisher,
    BondQuoteOutput,
    CurvePublisher,
    EtfAnalyticsOutput,
    EtfPublisher,
    OutputPublisher,
    PortfolioAnalyticsOutput,
    QuotePublisher,
)
from fuggers_py.core import CurveId, InstrumentId
from fuggers_py.market.snapshot import CurveInputs, CurvePoint


class CollectingQuotePublisher:
    def __init__(self) -> None:
        self.quotes: list[BondQuoteOutput] = []

    def publish_quote(self, quote: BondQuoteOutput) -> None:
        self.quotes.append(quote)


class CollectingCurvePublisher:
    def __init__(self) -> None:
        self.curves: list[tuple[CurveId | str, CurveInputs]] = []

    def publish_curve(self, curve_id: CurveId | str, curve: CurveInputs) -> None:
        self.curves.append((curve_id, curve))


class CollectingEtfPublisher:
    def __init__(self) -> None:
        self.etfs: list[EtfAnalyticsOutput] = []

    def publish_etf(self, analytics: EtfAnalyticsOutput) -> None:
        self.etfs.append(analytics)


class CollectingAnalyticsPublisher:
    def __init__(self) -> None:
        self.analytics: list[object] = []

    def publish_analytics(self, analytics: object) -> None:
        self.analytics.append(analytics)


class CollectingAlertPublisher:
    def __init__(self) -> None:
        self.alerts: list[tuple[str, str]] = []

    def publish_alert(self, message: str, *, severity: str = "info") -> None:
        self.alerts.append((message, severity))


def test_output_publishers_and_metadata_fields_remain_easy_to_use() -> None:
    quote = BondQuoteOutput(
        instrument_id=InstrumentId("PUBLISH-1"),
        clean_price=Decimal("101.25"),
        dv01=Decimal("0.042"),
        settlement_date=Date.from_ymd(2026, 3, 13),
        source="router",
        bid_price=Decimal("101.10"),
        ask_price=Decimal("101.40"),
        ytc=Decimal("0.0405"),
    )
    curve = CurveInputs.from_points(
        CurveId("usd.discount"),
        Date.from_ymd(2026, 3, 13),
        [CurvePoint(Decimal("1.0"), Decimal("0.04"))],
    )
    etf = EtfAnalyticsOutput(nav=Decimal("101.10"), aggregate_dv01=Decimal("12.5"))
    portfolio = PortfolioAnalyticsOutput(total_market_value=Decimal("1000000"), aggregate_dv01=Decimal("25.0"))

    publisher = OutputPublisher(
        quote_publisher=CollectingQuotePublisher(),
        curve_publisher=CollectingCurvePublisher(),
        etf_publisher=CollectingEtfPublisher(),
        analytics_publisher=CollectingAnalyticsPublisher(),
        alert_publisher=CollectingAlertPublisher(),
    )

    assert isinstance(publisher, QuotePublisher)
    assert isinstance(publisher, CurvePublisher)
    assert isinstance(publisher, EtfPublisher)
    assert isinstance(publisher, AnalyticsPublisher)
    publisher.publish_quote(quote)
    publisher.publish_curve("usd.discount", curve)
    publisher.publish_etf(etf)
    publisher.publish_analytics(portfolio)
    publisher.publish_alert("curve stale", severity="warn")

    assert quote.pv01 == Decimal("0.042")
    assert quote.mid_price == Decimal("101.25")
    assert etf.pv01 == Decimal("12.5")
    assert portfolio.pv01 == Decimal("25.0")
    assert publisher.quote_publisher.quotes == [quote]
    assert publisher.curve_publisher.curves[0][0] == "usd.discount"
    assert publisher.etf_publisher.etfs == [etf]
    assert publisher.analytics_publisher.analytics == [portfolio]
    assert publisher.alert_publisher.alerts == [("curve stale", "warn")]
