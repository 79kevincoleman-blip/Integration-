from pretrade import pretrade_check

PAPER_OK = {"closed_trades": 30, "expectancy_r": 0.25}
GOOD = dict(ticker="X", price=12.0, bid=11.99, ask=12.01, market_cap=5e9, entry=12.0, stop=10.8, prior_close=11.9,
            order_type="LIMIT", et_time="09:30", cash=200.0, setup_signal=True)


def test_go_and_50pct_sizing():
    r = pretrade_check(GOOD, PAPER_OK)
    assert r["verdict"] == "GO", r["reasons"]
    # no balance given -> $150 fallback; 50% = $75 at $12 -> 6.25 sh
    assert r["shares"] == 6.25 and r["position_usd"] == 75.0


def test_real_balance_used():
    r = pretrade_check(dict(GOOD, account_value=300.0, cash=300.0), PAPER_OK)
    assert r["position_usd"] == 150.0  # 50% of the real $300 balance


def test_tier_stops():
    from pretrade import tier_stop
    assert tier_stop(4.0) == 2.0 and tier_stop(5.0) == 2.5      # 50%
    assert tier_stop(8.0) == 6.0 and tier_stop(10.0) == 7.5     # 25%
    assert tier_stop(12.0) == 9.6 and tier_stop(15.0) == 12.0   # 20%
    r = pretrade_check(dict(GOOD, stop=11.9), PAPER_OK)          # written stop ignored
    assert r["stop"] == 9.6 and r["exit_after_days"] == 60


def test_never_more_than_available_balance():
    # owner example: 18 sh at $4 = $72 of $150 -> only ~$78 cash left for the next buy
    r = pretrade_check(dict(GOOD, cash=78.0, account_value=150.0), PAPER_OK)
    assert r["position_usd"] == 75.0
    r = pretrade_check(dict(GOOD, cash=10.0), PAPER_OK)
    assert r["position_usd"] == 10.0
    assert "no available balance" in pretrade_check(dict(GOOD, cash=0), PAPER_OK)["reasons"]


def test_max_10_positions():
    assert "max 10" in " ".join(pretrade_check(dict(GOOD, open_positions=10), PAPER_OK)["reasons"])
    assert pretrade_check(dict(GOOD, open_positions=9), PAPER_OK)["verdict"] == "GO"


def test_price_at_or_under_15():
    t = dict(GOOD, price=15.01, bid=15.0, ask=15.02, entry=15.01, prior_close=15.0)
    assert "over $15" in " ".join(pretrade_check(t, PAPER_OK)["reasons"])
    t = dict(GOOD, price=15.0, bid=14.99, ask=15.01, entry=15.0, prior_close=14.9)
    assert pretrade_check(t, PAPER_OK)["verdict"] == "GO"


def test_no_entry_is_no_go():
    r = pretrade_check(dict(GOOD, entry=None), PAPER_OK)
    assert r["verdict"] == "NO-GO" and "no written" in r["reasons"][0]


def test_penny_limits_still_apply():
    r = pretrade_check(dict(GOOD, price=3.7, market_cap=4e7, bid=3.55, ask=4.0, entry=3.7, stop=3.15, prior_close=3.7), PAPER_OK)
    txt = " ".join(r["reasons"])
    assert "market cap" in txt and "spread" in txt and "52-week" in txt and "filings" in txt


def test_clean_penny_can_pass():
    t = dict(GOOD, price=4.0, bid=3.995, ask=4.005, market_cap=2e8, entry=4.0, stop=3.6, prior_close=3.95,
             new_52w_low_5d=False, filings_ok=True, fees=0.0)
    assert pretrade_check(t, PAPER_OK)["verdict"] == "GO", pretrade_check(t, PAPER_OK)["reasons"]


def test_costs_vs_risk():
    r = pretrade_check(dict(GOOD, bid=11.8, ask=12.2), PAPER_OK)  # 3.3% spread
    assert "max 20%" in " ".join(r["reasons"])


def test_no_chasing_gap_and_limit_only():
    assert "more than 2% above" in " ".join(pretrade_check(dict(GOOD, prior_close=11.5), PAPER_OK)["reasons"])
    assert "LIMIT" in " ".join(pretrade_check(dict(GOOD, order_type="MARKET"), PAPER_OK)["reasons"])


def test_needs_kim_signal():
    assert "Kim-daily" in " ".join(pretrade_check(dict(GOOD, setup_signal=False), PAPER_OK)["reasons"])


def test_paper_gate_blocks():
    r = pretrade_check(GOOD, {"closed_trades": 12, "expectancy_r": 0.5})
    assert r["verdict"] == "NO-GO" and "paper gate" in r["reasons"][-1]


def test_owner_has_final_say():
    from pretrade import owner_decision
    nogo = pretrade_check(dict(GOOD, setup_signal=False), PAPER_OK)
    assert nogo["final_say"] == "OWNER"
    d = owner_decision(nogo, "GO")
    assert d["create_order"] and "OVERRIDE" in d["note"]
    go = pretrade_check(GOOD, PAPER_OK)
    assert owner_decision(go, "no")["create_order"] is False
