import json

import pytest

from arbitrage.adapters import get_marketplace
from arbitrage.adapters.supplier import SupplierFeedMarketplace

CSV = """sku,name,wholesale_price,shipping,category
A1,Cheap Widget,3.50,1.00,gadgets
A2,Another Thing,10,0,home
,No SKU Row,5,0,x
B3,No Price Row,,0,x
"""

JSON_FEED = [
    {"id": "J1", "title": "Json Widget", "cost": "$7.99", "ship_cost": "2"},
]


def test_requires_feed():
    with pytest.raises(ValueError):
        SupplierFeedMarketplace()


def test_parse_csv_skips_invalid_rows(tmp_path):
    f = tmp_path / "feed.csv"
    f.write_text(CSV, encoding="utf-8")
    m = SupplierFeedMarketplace(feed=str(f))
    items = m.fetch_catalog()
    skus = {p.sku for p in items}
    assert skus == {"A1", "A2"}  # rows missing sku/price are dropped
    a1 = next(p for p in items if p.sku == "A1")
    assert a1.price == 3.5 and a1.shipping == 1.0
    assert a1.landed_cost == 4.5


def test_parse_json_with_currency_symbols(tmp_path):
    f = tmp_path / "feed.json"
    f.write_text(json.dumps(JSON_FEED), encoding="utf-8")
    m = SupplierFeedMarketplace(feed=str(f))
    items = m.fetch_catalog()
    assert len(items) == 1
    assert items[0].price == 7.99 and items[0].shipping == 2.0


def test_registry_exposes_supplier(tmp_path):
    f = tmp_path / "feed.csv"
    f.write_text(CSV, encoding="utf-8")
    m = get_marketplace("supplier", feed=str(f))
    assert isinstance(m, SupplierFeedMarketplace)
    assert m.search("widget")[0].sku == "A1"
