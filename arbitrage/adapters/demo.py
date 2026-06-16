"""Demo marketplace backed by bundled JSON catalogs (works fully offline).

Optionally, if ``live=True`` and the network is available, it augments the
catalog with real products from the free Fake Store API
(https://fakestoreapi.com) so you can watch the engine run against live data
without any API keys.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Product
from .base import Marketplace

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class DemoMarketplace(Marketplace):
    name = "demo"

    def __init__(self, dataset: str = "source", live: bool = False, data_dir: Path | None = None):
        self.dataset = dataset
        self.live = live
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self._cache: list[Product] | None = None

    def _load_file(self) -> list[Product]:
        path = self.data_dir / f"{self.dataset}_catalog.json"
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Product(**item) for item in raw]

    def _load_live(self) -> list[Product]:
        try:
            import requests  # local import so offline use needs no dep

            resp = requests.get("https://fakestoreapi.com/products", timeout=10)
            resp.raise_for_status()
            products = []
            for item in resp.json():
                # Simulate a price gap: the "source" sells cheaper than "target".
                base = float(item["price"])
                price = base if self.dataset == "source" else round(base * 1.6 + 4, 2)
                products.append(
                    Product(
                        sku=f"FS-{item['id']}",
                        title=item["title"],
                        price=price,
                        url=f"https://fakestoreapi.com/products/{item['id']}",
                        image=item.get("image"),
                        category=item.get("category"),
                    )
                )
            return products
        except Exception:
            return []

    def fetch_catalog(self, *, limit: int = 100) -> list[Product]:
        if self._cache is None:
            items = self._load_file()
            if self.live:
                items = items + self._load_live()
            self._cache = items
        return self._cache[:limit]

    def search(self, query: str, *, limit: int = 50) -> list[Product]:
        q = query.lower().strip()
        results = [
            p for p in self.fetch_catalog(limit=1000)
            if not q or q in p.title.lower() or (p.category and q in p.category.lower())
        ]
        return results[:limit]
