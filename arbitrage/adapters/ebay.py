"""eBay marketplace adapter using the official Browse API.

Requires an eBay developer application token. Get one at
https://developer.ebay.com (free). Set EBAY_OAUTH_TOKEN in your environment, or
pass ``token=`` to the constructor. Use ``sandbox=True`` while testing.

This adapter only *reads* listings (to find sell prices / source prices). Posting
listings is done via the eBay Sell API and is intentionally a separate,
explicit step (see ``arbitrage.listing``) so nothing auto-transacts.
"""

from __future__ import annotations

import os

from ..models import Product
from .base import Marketplace

PROD_BASE = "https://api.ebay.com"
SANDBOX_BASE = "https://api.sandbox.ebay.com"


class EbayMarketplace(Marketplace):
    name = "ebay"

    def __init__(
        self,
        token: str | None = None,
        sandbox: bool = False,
        marketplace_id: str = "EBAY_US",
        **_ignored,
    ):
        self.token = token or os.environ.get("EBAY_OAUTH_TOKEN")
        self.base = SANDBOX_BASE if sandbox else PROD_BASE
        self.marketplace_id = marketplace_id

    def _headers(self) -> dict:
        if not self.token:
            raise RuntimeError(
                "No eBay token. Set EBAY_OAUTH_TOKEN or pass token=. "
                "Get one free at https://developer.ebay.com."
            )
        return {
            "Authorization": f"Bearer {self.token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            "Content-Type": "application/json",
        }

    def search(self, query: str, *, limit: int = 50) -> list[Product]:
        import requests

        url = f"{self.base}/buy/browse/v1/item_summary/search"
        resp = requests.get(
            url,
            headers=self._headers(),
            params={"q": query, "limit": min(limit, 200)},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        products: list[Product] = []
        for item in data.get("itemSummaries", []):
            price = item.get("price", {})
            ship = 0.0
            for opt in item.get("shippingOptions", []) or []:
                cost = opt.get("shippingCost", {})
                if cost.get("value") is not None:
                    ship = float(cost["value"])
                    break
            products.append(
                Product(
                    sku=item.get("itemId", item.get("epid", "")),
                    title=item.get("title", ""),
                    price=float(price.get("value", 0.0)),
                    currency=price.get("currency", "USD"),
                    url=item.get("itemWebUrl"),
                    image=(item.get("image") or {}).get("imageUrl"),
                    condition=item.get("condition", "new"),
                    category=", ".join(item.get("categories", [{}])[0].get("categoryName", "") for _ in [0]) or None,
                    shipping=ship,
                )
            )
        return products
