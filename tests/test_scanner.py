from arbitrage.adapters.demo import DemoMarketplace
from arbitrage.models import Product
from arbitrage.scanner import ScanConfig, match_products, scan


def test_demo_catalog_loads():
    src = DemoMarketplace(dataset="source")
    tgt = DemoMarketplace(dataset="target")
    assert len(src.fetch_catalog()) == 12
    assert len(tgt.fetch_catalog()) == 12


def test_match_by_sku():
    s = [Product(sku="A", title="alpha widget", price=1.0)]
    t = [Product(sku="A", title="totally different name", price=2.0)]
    pairs = match_products(s, t, min_match=0.9)
    assert len(pairs) == 1 and pairs[0][2] == 1.0


def test_match_by_title_fuzzy():
    s = [Product(sku="", title="Wireless Earbuds Bluetooth", price=1.0)]
    t = [Product(sku="", title="Wireless Earbuds Bluetooth ANC", price=2.0)]
    pairs = match_products(s, t, min_match=0.5)
    assert len(pairs) == 1 and pairs[0][2] >= 0.5


def test_scan_finds_profitable_and_filters_losers():
    src = DemoMarketplace(dataset="source")
    tgt = DemoMarketplace(dataset="target")
    cfg = ScanConfig(min_profit=1.0, min_roi=0.15, ship_to_customer=5.0)
    result = scan(src, tgt, cfg)
    assert result.scanned_source == 12
    assert len(result.opportunities) > 0
    # The car mount (WID-008) is a known loser and must be filtered out.
    skus = {o.source.sku for o in result.opportunities}
    assert "WID-008" not in skus
    # Sorted by ROI descending.
    rois = [o.roi for o in result.opportunities]
    assert rois == sorted(rois, reverse=True)
