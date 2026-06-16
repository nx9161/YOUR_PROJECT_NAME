from arbitrage.fees import evaluate, get_fee_schedule
from arbitrage.listing import make_listing, optimize_title, suggest_price
from arbitrage.models import Product


def _opp():
    src = Product(sku="WID-001", title="Wireless Earbuds", price=12.5, url="http://s")
    tgt = Product(sku="WID-001", title="Wireless Earbuds Bluetooth 5.3 ANC", price=34.99)
    return evaluate(src, tgt, get_fee_schedule("ebay"), ship_to_customer=5.0)


def test_optimize_title_length_and_keywords():
    title = optimize_title("Wireless Earbuds Bluetooth 5.3 Active Noise Cancelling In-Ear")
    assert len(title) <= 80
    assert "Wireless" in title


def test_suggested_price_not_below_breakeven():
    from arbitrage.fees import breakeven_sell_price

    opp = _opp()
    fees = get_fee_schedule("ebay")
    price = suggest_price(opp, fees, target_margin=0.20)
    be = breakeven_sell_price(opp.buy_cost, fees, opp.ship_to_customer)
    assert price >= be
    assert price <= opp.target.price


def test_make_listing_fields():
    listing = make_listing(_opp(), "ebay")
    assert listing.sku == "WID-001"
    assert listing.suggested_price > 0
    assert listing.projected_profit > 0
    assert "Condition" in listing.description
