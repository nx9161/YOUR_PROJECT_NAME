"""Core data models for the arbitrage engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Product:
    """A product offer from a single marketplace."""

    sku: str
    title: str
    price: float
    currency: str = "USD"
    url: str | None = None
    image: str | None = None
    condition: str = "new"
    category: str | None = None
    # Estimated shipping the buyer pays to receive the item from this market.
    shipping: float = 0.0

    @property
    def landed_cost(self) -> float:
        """Total cost to acquire one unit from this market."""
        return round(self.price + self.shipping, 2)


@dataclass(frozen=True)
class FeeSchedule:
    """Fees charged by the *target* marketplace when you sell."""

    name: str = "generic"
    # Final-value / commission fee as a fraction of (price + buyer shipping).
    commission_rate: float = 0.10
    # Payment processing fee as a fraction of the order total.
    payment_rate: float = 0.029
    # Fixed per-order fee (e.g. payment processor flat fee).
    fixed_fee: float = 0.30
    # Sales tax you must remit as a fraction (usually marketplace-collected;
    # kept configurable for completeness, default 0 since it's pass-through).
    tax_rate: float = 0.0


@dataclass(frozen=True)
class Opportunity:
    """A matched buy/sell pair with computed economics."""

    source: Product
    target: Product
    units: int
    buy_cost: float
    sell_revenue: float
    fees: float
    ship_to_customer: float
    net_profit: float
    roi: float  # net_profit / buy_cost
    margin: float  # net_profit / sell_revenue
    match_score: float = 1.0
    notes: str = ""

    def as_row(self) -> dict:
        return {
            "sku": self.source.sku,
            "title": self.source.title[:60],
            "buy": round(self.buy_cost, 2),
            "sell": round(self.sell_revenue, 2),
            "fees": round(self.fees, 2),
            "ship": round(self.ship_to_customer, 2),
            "profit": round(self.net_profit, 2),
            "roi_%": round(self.roi * 100, 1),
            "margin_%": round(self.margin * 100, 1),
            "match": round(self.match_score, 2),
        }


@dataclass
class ScanResult:
    """Summary of a scan run."""

    opportunities: list[Opportunity] = field(default_factory=list)
    scanned_source: int = 0
    scanned_target: int = 0

    @property
    def profitable(self) -> list[Opportunity]:
        return [o for o in self.opportunities if o.net_profit > 0]
