"""Marketplace adapters.

Each adapter exposes a uniform interface so the scanner does not care whether
products come from a free demo API, eBay, Amazon, etc.
"""

from .base import Marketplace
from .demo import DemoMarketplace
from .ebay import EbayMarketplace

REGISTRY: dict[str, type[Marketplace]] = {
    "demo": DemoMarketplace,
    "ebay": EbayMarketplace,
}


def get_marketplace(name: str, **kwargs) -> Marketplace:
    name = name.lower()
    if name not in REGISTRY:
        raise ValueError(
            f"Unknown marketplace '{name}'. Available: {', '.join(REGISTRY)}"
        )
    return REGISTRY[name](**kwargs)


__all__ = ["Marketplace", "DemoMarketplace", "EbayMarketplace", "get_marketplace", "REGISTRY"]
