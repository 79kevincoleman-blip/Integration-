from webull_strategy import *

def bar(h, l, c, v=100):
    return {"high": h, "low": l, "close": c, "volume": v}

def downtrend(n=20, start=20.0):
    return [bar(start - i * 0.1 + 0.2, start - i * 0.1 - 0.2, start - i * 0.1) for i in range(n)]

def test_timeframe():
    assert timeframe(0.02) == "DAILY"
    assert timeframe(0.05) == "INTRADAY"
    assert timeframe(0.02, has_news=True) == "INTRADAY"

def test_still_falling_is_watch():
    assert evaluate(downtrend(), 100)[0] == "WATCH"

def test_reversal_at_lowest_low_buys():
    b = downtrend()
    b.append(bar(18.5, 17.95, 18.4, 200))  # near the low, closes above prior high on volume
    decision, sig, low = evaluate(b, 100)
    assert decision == "BUY_LOW" and "close_above_prior_high" in sig

def test_plan_two_to_one():
    p = plan(10.5, 10.0, 1000)
    assert p["stop"] == 9.9 and p["target"] == 11.7
