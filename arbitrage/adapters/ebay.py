"""eBay marketplace adapter using the official Browse API.

Authentication (pick one):
  * Easiest: set ``EBAY_CLIENT_ID`` and ``EBAY_CLIENT_SECRET`` (your app's
    App ID / Cert ID from https://developer.ebay.com). The adapter fetches and
    caches an application OAuth token automatically via the client-credentials
    flow.
  * Or set ``EBAY_OAUTH_TOKEN`` directly (a pre-minted token), or pass
    ``token=`` to the constructor.
Use ``sandbox=True`` while testing.

This adapter only *reads* listings (to find sell prices / source prices). Posting
listings is done via the eBay Sell API and is intentionally a separate,
explicit step (see ``arbitrage.listing``) so nothing auto-transacts.
"""

from __future__ import annotations

import base64
import os
import time

from ..models import Product
from .base import Marketplace

PROD_BASE = "https://api.ebay.com"
SANDBOX_BASE = "https://api.sandbox.ebay.com"
# Public data scope is enough for the Browse API.
BROWSE_SCOPE = "https://api.ebay.com/oauth/api_scope"


class EbayMarketplace(Marketplace):
    name = "ebay"

    def __init__(
        self,
        token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        sandbox: bool = False,
        marketplace_id: str = "EBAY_US",
        **_ignored,
    ):
        self.token = token or os.environ.get("EBAY_OAUTH_TOKEN")
        self.client_id = client_id or os.environ.get("EBAY_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("EBAY_CLIENT_SECRET")
        self.sandbox = sandbox
        self.base = SANDBOX_BASE if sandbox else PROD_BASE
        self.marketplace_id = marketplace_id
        self._token_expiry = 0.0

    def _fetch_app_token(self) -> str:
        import requests

        creds = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        resp = requests.post(
            f"{self.base}/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": BROWSE_SCOPE},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        self.token = payload["access_token"]
        # Refresh a minute early to be safe.
        self._token_expiry = time.time() + int(payload.get("expires_in", 7200)) - 60
        return self.token

    def _ensure_token(self) -> str:
        if self.token and time.time() < self._token_expiry:
            return self.token
        if self.client_id and self.client_secret:
            return self._fetch_app_token()
        if self.token:
            return self.token
        raise RuntimeError(
            "No eBay credentials. Set EBAY_CLIENT_ID + EBAY_CLIENT_SECRET "
            "(recommended) or EBAY_OAUTH_TOKEN. Get them free at "
            "https://developer.ebay.com."
        )

    def _headers(self) -> dict:
        self._ensure_token()
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
