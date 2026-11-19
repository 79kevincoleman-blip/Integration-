from pretrade import pretrade_check

PAPER_OK = {"closed_trades": 30, "expectancy_r": 0.25}
GOOD = dict(ticker="X", price=20.0, bid=19.99, ask=20.01, market_cap=5e9, entry=20.0, stop=19.0,
            target=22.5, order_type="LIMIT", et_time="10:15", cash=30.0, setup_signal=True)

def test_go():
    r = pretrade_check(GOOD, PAPER_OK)
    assert r["verdict"] == "GO", r["reasons"]
    assert r["risk_usd"] == 1.5 and r["shares"] == 1.5 and r["position_usd"] == 30.0

def test_no_stop_is_no_go():
    r = pretrade_check(dict(GOOD, stop=None), PAPER_OK)
    assert r["verdict"] == "NO-GO" and "no written" in r["reasons"][0]

def test_universe_and_costs():
    r = pretrade_check(dict(GOOD, price=3.7, market_cap=4e7, bid=3.55, ask=4.0, entry=3.7, stop=3.15, target=4.0), PAPER_OK)
    txt = " ".join(r["reasons"])
    assert "price" in txt and "market cap" in txt and "spread" in txt and "reward:risk" in txt

def test_breakeven_math():
    r = pretrade_check(dict(GOOD, bid=20.0, ask=20.0, fees=0, target=22.0), PAPER_OK)
    assert r["breakeven_win_rate_no_costs"] == 33.3 and r["breakeven_win_rate_after_costs"] == 33.3

def test_paper_gate_blocks():
    r = pretrade_check(GOOD, {"closed_trades": 12, "expectancy_r": 0.5})
    assert r["verdict"] == "NO-GO" and "paper gate" in r["reasons"][-1]
