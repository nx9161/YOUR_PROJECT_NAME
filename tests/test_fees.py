from arbitrage.fees import (
    breakeven_sell_price,
    compute_fees,
    evaluate,
    get_fee_schedule,
)
from arbitrage.models import Product


def test_compute_fees_ebay():
    fees = get_fee_schedule("ebay")
    # 13.25% of 100 + $0.30 fixed = 13.55
    assert compute_fees(100.0, 0.0, fees) == 13.55


def test_compute_fees_includes_buyer_shipping_in_base():
    fees = get_fee_schedule("ebay")
    # base is price + buyer shipping = 110
    assert compute_fees(100.0, 10.0, fees) == round(110 * 0.1325 + 0.30, 2)


def test_evaluate_profit_positive():
    src = Product(sku="X", title="thing", price=10.0)
    tgt = Product(sku="X", title="thing", price=40.0)
    fees = get_fee_schedule("ebay")
    opp = evaluate(src, tgt, fees, ship_to_customer=5.0)
    # revenue 40 - buy 10 - fees(40*.1325+.3=5.6) - ship 5 = 19.40
    assert opp.net_profit == 19.40
    assert round(opp.roi, 2) == 1.94
    assert 0 < opp.margin < 1


def test_evaluate_loss_is_negative():
    src = Product(sku="X", title="thing", price=8.0)
    tgt = Product(sku="X", title="thing", price=9.99)
    opp = evaluate(src, tgt, get_fee_schedule("ebay"), ship_to_customer=5.0)
    assert opp.net_profit < 0


def test_breakeven_round_trip():
    fees = get_fee_schedule("ebay")
    be = breakeven_sell_price(10.0, fees, ship_to_customer=5.0)
    src = Product(sku="X", title="t", price=10.0)
    tgt = Product(sku="X", title="t", price=be)
    opp = evaluate(src, tgt, fees, ship_to_customer=5.0)
    assert abs(opp.net_profit) <= 0.05  # ~breakeven within rounding


def test_units_scale_linearly():
    src = Product(sku="X", title="t", price=10.0)
    tgt = Product(sku="X", title="t", price=40.0)
    fees = get_fee_schedule("ebay")
    one = evaluate(src, tgt, fees, ship_to_customer=5.0, units=1)
    three = evaluate(src, tgt, fees, ship_to_customer=5.0, units=3)
    assert round(three.net_profit, 2) == round(one.net_profit * 3, 2)
