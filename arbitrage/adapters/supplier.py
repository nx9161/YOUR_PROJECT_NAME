"""Supplier feed adapter: read a real dropship/wholesale catalog from CSV or JSON.

Most suppliers (and tools like Inventory Source, Spocket exports, AliExpress
dropship lists, distributor price sheets) provide a CSV or JSON feed. Point this
adapter at a local file or an http(s) URL and it becomes a usable *source*
market for the scanner.

Expected columns (CSV) / keys (JSON), case-insensitive, with common aliases:
    sku | id            (required)
    title | name | description
    price | cost | wholesale_price   (required)
    shipping | ship_cost   (default 0)
    url | link
    image | image_url
    condition
    category
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from ..models import Product
from .base import Marketplace

_ALIASES: dict[str, tuple[str, ...]] = {
    "sku": ("sku", "id", "item_id", "product_id"),
    "title": ("title", "name", "description", "product_name"),
    "price": ("price", "cost", "wholesale_price", "buy_price", "unit_cost"),
    "shipping": ("shipping", "ship_cost", "shipping_cost", "freight"),
    "url": ("url", "link", "product_url"),
    "image": ("image", "image_url", "img", "thumbnail"),
    "condition": ("condition", "cond"),
    "category": ("category", "cat", "type"),
}


def _pick(row: dict, field: str) -> str | None:
    lower = {k.lower().strip(): v for k, v in row.items() if k}
    for alias in _ALIASES[field]:
        if alias in lower and lower[alias] not in (None, ""):
            return str(lower[alias])
    return None


def _to_product(row: dict) -> Product | None:
    sku = _pick(row, "sku")
    title = _pick(row, "title")
    price_raw = _pick(row, "price")
    if not sku or not title or price_raw is None:
        return None
    try:
        price = float(str(price_raw).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None
    ship_raw = _pick(row, "shipping")
    try:
        shipping = float(str(ship_raw).replace("$", "").strip()) if ship_raw else 0.0
    except ValueError:
        shipping = 0.0
    return Product(
        sku=sku,
        title=title,
        price=price,
        shipping=shipping,
        url=_pick(row, "url"),
        image=_pick(row, "image"),
        condition=_pick(row, "condition") or "new",
        category=_pick(row, "category"),
    )


class SupplierFeedMarketplace(Marketplace):
    name = "supplier"

    def __init__(self, feed: str | None = None, **_ignored):
        if not feed:
            raise ValueError(
                "SupplierFeedMarketplace requires feed=<path-or-url> "
                "(CSV or JSON). e.g. --source supplier --source-feed catalog.csv"
            )
        self.feed = feed
        self._cache: list[Product] | None = None

    def _read_raw(self) -> str:
        if self.feed.lower().startswith(("http://", "https://")):
            import requests

            resp = requests.get(self.feed, timeout=30)
            resp.raise_for_status()
            return resp.text
        return Path(self.feed).read_text(encoding="utf-8")

    def _parse(self, text: str) -> list[Product]:
        stripped = text.lstrip()
        rows: list[dict]
        if stripped.startswith("[") or stripped.startswith("{"):
            data = json.loads(text)
            rows = data if isinstance(data, list) else data.get("products", [])
        else:
            rows = list(csv.DictReader(io.StringIO(text)))
        products = [p for p in (_to_product(r) for r in rows) if p is not None]
        return products

    def fetch_catalog(self, *, limit: int = 100) -> list[Product]:
        if self._cache is None:
            self._cache = self._parse(self._read_raw())
        return self._cache[:limit]

    def search(self, query: str, *, limit: int = 50) -> list[Product]:
        q = query.lower().strip()
        items = [
            p for p in self.fetch_catalog(limit=10_000)
            if not q or q in p.title.lower() or (p.category and q in p.category.lower())
        ]
        return items[:limit]
