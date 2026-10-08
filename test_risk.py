import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))
from risk import *
import config

def test_stops():
    assert stop_pct_for_price(20) == 0.15
    assert stop_pct_for_price(500) == 0.20
    assert stop_pct_for_price(1500, no_news=True) == 0.10
    assert stop_pct_for_price(20, atr_pct=0.25) == 0.25

def test_two_percent_cap():
    # $20 stock, 15% stop: 2% of 5000 = $100 risk -> $666 position cap, 15% size = $750
    s = shares_to_buy(20, 0.15, 0, 5000)
    assert abs(s * 20 - 666.67) < 1

def test_blocks():
    assert shares_to_buy(20, 0.15, 8, 5000) == 0
    assert shares_to_buy(20, 0.15, 0, 400) == 0   # cash under 10% floor

def test_pause():
    assert should_pause(3400) and not should_pause(3600)

def test_guard():
    os.environ["ALPACA_BASE_URL"] = "https://api.alpaca.markets"
    try:
        config.get_base_url(); assert False
    except SystemExit:
        pass
    del os.environ["ALPACA_BASE_URL"]
