"""Arbitrage scanner: match source<->target products and rank by profit."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .adapters.base import Marketplace
from .fees import FeeSchedule, evaluate, get_fee_schedule
from .models import Product, ScanResult


@dataclass
class ScanConfig:
    fee_schedule: str = "ebay"
    min_profit: float = 1.0          # absolute $ per unit
    min_roi: float = 0.15            # 15% return on cost
    min_match: float = 0.55          # fuzzy title similarity threshold
    ship_to_customer: float = 5.0    # your cost to ship to the buyer
    buyer_shipping: float = 0.0      # what the buyer pays for shipping
    units: int = 1
    limit: int = 200


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match_products(
    sources: list[Product], targets: list[Product], min_match: float
) -> list[tuple[Product, Product, float]]:
    """Pair each source with its best target match (by SKU, then title)."""
    by_sku = {t.sku: t for t in targets if t.sku}
    pairs: list[tuple[Product, Product, float]] = []
    for s in sources:
        if s.sku and s.sku in by_sku:
            pairs.append((s, by_sku[s.sku], 1.0))
            continue
        best: Product | None = None
        best_score = 0.0
        for t in targets:
            score = _title_similarity(s.title, t.title)
            if score > best_score:
                best, best_score = t, score
        if best is not None and best_score >= min_match:
            pairs.append((s, best, best_score))
    return pairs


def scan(
    source: Marketplace,
    target: Marketplace,
    config: ScanConfig,
    *,
    query: str = "",
    fees: FeeSchedule | None = None,
) -> ScanResult:
    fees = fees or get_fee_schedule(config.fee_schedule)

    sources = source.search(query, limit=config.limit) if query else source.fetch_catalog(limit=config.limit)
    targets = target.search(query, limit=config.limit) if query else target.fetch_catalog(limit=config.limit)

    result = ScanResult(scanned_source=len(sources), scanned_target=len(targets))

    for s, t, match_score in match_products(sources, targets, config.min_match):
        opp = evaluate(
            s,
            t,
            fees,
            units=config.units,
            ship_to_customer=config.ship_to_customer,
            buyer_shipping=config.buyer_shipping,
            match_score=match_score,
        )
        if opp.net_profit >= config.min_profit and opp.roi >= config.min_roi:
            result.opportunities.append(opp)

    result.opportunities.sort(key=lambda o: (o.roi, o.net_profit), reverse=True)
    return result
