"""Profit math: turn a buy price + sell price into net profit after costs.

This is the heart of the engine. Get this wrong and you lose money on every
sale, so it is fully unit-tested.
"""

from __future__ import annotations

from .models import FeeSchedule, Opportunity, Product

# A few real-world default fee schedules (approximate; verify before relying).
FEE_SCHEDULES: dict[str, FeeSchedule] = {
    "generic": FeeSchedule("generic", commission_rate=0.10),
    # eBay final value fee varies by category; ~13.25% + $0.30 is a common rate.
    "ebay": FeeSchedule("ebay", commission_rate=0.1325, payment_rate=0.0, fixed_fee=0.30),
    # Amazon referral fee ~15% (category dependent), no separate payment fee.
    "amazon": FeeSchedule("amazon", commission_rate=0.15, payment_rate=0.0, fixed_fee=0.0),
    # Mercari ~10% + payment processing 2.9% + $0.50.
    "mercari": FeeSchedule("mercari", commission_rate=0.10, payment_rate=0.029, fixed_fee=0.50),
    # Facebook Marketplace shipping orders ~5% (min $0.40).
    "facebook": FeeSchedule("facebook", commission_rate=0.05, payment_rate=0.0, fixed_fee=0.40),
}


def get_fee_schedule(name: str) -> FeeSchedule:
    return FEE_SCHEDULES.get(name.lower(), FEE_SCHEDULES["generic"])


def compute_fees(sell_price: float, buyer_shipping: float, fees: FeeSchedule) -> float:
    """Total fees the marketplace + payment processor take from one sale."""
    order_total = sell_price + buyer_shipping
    commission = order_total * fees.commission_rate
    payment = order_total * fees.payment_rate
    tax = order_total * fees.tax_rate
    total = commission + payment + tax + fees.fixed_fee
    return round(total, 2)


def evaluate(
    source: Product,
    target: Product,
    fees: FeeSchedule,
    *,
    units: int = 1,
    ship_to_customer: float = 0.0,
    buyer_shipping: float = 0.0,
    match_score: float = 1.0,
) -> Opportunity:
    """Compute the economics of buying ``source`` and reselling as ``target``.

    - ``ship_to_customer``: what it costs YOU to ship the item to the buyer.
    - ``buyer_shipping``: what the buyer pays on top of the item price (adds to
      revenue but also to the fee base).
    """
    buy_cost = source.landed_cost * units
    sell_revenue = (target.price + buyer_shipping) * units
    fee_total = compute_fees(target.price, buyer_shipping, fees) * units
    ship_cost = ship_to_customer * units

    net_profit = round(sell_revenue - buy_cost - fee_total - ship_cost, 2)
    roi = net_profit / buy_cost if buy_cost else 0.0
    margin = net_profit / sell_revenue if sell_revenue else 0.0

    return Opportunity(
        source=source,
        target=target,
        units=units,
        buy_cost=round(buy_cost, 2),
        sell_revenue=round(sell_revenue, 2),
        fees=fee_total,
        ship_to_customer=round(ship_cost, 2),
        net_profit=net_profit,
        roi=round(roi, 4),
        margin=round(margin, 4),
        match_score=match_score,
    )


def breakeven_sell_price(
    buy_cost: float, fees: FeeSchedule, ship_to_customer: float = 0.0
) -> float:
    """Lowest sell price (excluding buyer shipping) that yields >= $0 profit."""
    # net = price - fixed - price*(rates) - buy - ship  >= 0
    rates = fees.commission_rate + fees.payment_rate + fees.tax_rate
    numerator = buy_cost + ship_to_customer + fees.fixed_fee
    denom = 1 - rates
    if denom <= 0:
        return float("inf")
    return round(numerator / denom, 2)
