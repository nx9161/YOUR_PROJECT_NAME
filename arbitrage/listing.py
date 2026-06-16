"""Generate optimized listings + repricing for winning opportunities."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .fees import FeeSchedule, breakeven_sell_price, get_fee_schedule
from .models import Opportunity


@dataclass
class Listing:
    sku: str
    title: str
    description: str
    suggested_price: float
    breakeven_price: float
    source_url: str | None
    image: str | None
    projected_profit: float

    def to_dict(self) -> dict:
        return asdict(self)


_STOPWORDS = {"the", "a", "an", "and", "or", "with", "for", "of", "to", "in"}


def _keywords(title: str, limit: int = 8) -> list[str]:
    seen: list[str] = []
    for word in title.replace("/", " ").replace("-", " ").split():
        w = word.strip().strip(",.()").lower()
        if w and w not in _STOPWORDS and w not in seen and len(w) > 1:
            seen.append(w)
        if len(seen) >= limit:
            break
    return seen


def optimize_title(raw: str, condition: str = "new", max_len: int = 80) -> str:
    """eBay/Amazon-style keyword-front-loaded title, capped at max_len chars."""
    kws = _keywords(raw, limit=12)
    cond = "Brand New" if condition == "new" else condition.title()
    title = " ".join(w.capitalize() for w in kws)
    title = f"{title} - {cond} - Fast Free Shipping"
    return title[:max_len].rstrip(" -")


def build_description(opp: Opportunity) -> str:
    p = opp.target
    bullets = "\n".join(f"- {k.capitalize()}" for k in _keywords(p.title, limit=5))
    return (
        f"{p.title}\n\n"
        f"Condition: {p.condition.title()}\n"
        f"Highlights:\n{bullets}\n\n"
        "Ships fast with tracking. Buy with confidence — satisfaction guaranteed. "
        "Message us with any questions!"
    )


def suggest_price(
    opp: Opportunity, fees: FeeSchedule, target_margin: float = 0.20
) -> float:
    """Price so that net margin ~= target_margin, but never below breakeven."""
    be = breakeven_sell_price(opp.buy_cost / opp.units, fees, opp.ship_to_customer / opp.units)
    rates = fees.commission_rate + fees.payment_rate + fees.tax_rate
    cost = (opp.buy_cost + opp.ship_to_customer) / opp.units
    denom = 1 - rates - target_margin
    if denom <= 0:
        return round(max(be, opp.target.price), 2)
    target_price = (cost + fees.fixed_fee) / denom
    return round(max(be, min(target_price, opp.target.price)), 2)


def make_listing(opp: Opportunity, fee_schedule: str = "ebay", target_margin: float = 0.20) -> Listing:
    fees = get_fee_schedule(fee_schedule)
    price = suggest_price(opp, fees, target_margin)
    be = breakeven_sell_price(opp.buy_cost / opp.units, fees, opp.ship_to_customer / opp.units)
    return Listing(
        sku=opp.source.sku,
        title=optimize_title(opp.target.title, opp.target.condition),
        description=build_description(opp),
        suggested_price=price,
        breakeven_price=be,
        source_url=opp.source.url,
        image=opp.target.image or opp.source.image,
        projected_profit=opp.net_profit,
    )
