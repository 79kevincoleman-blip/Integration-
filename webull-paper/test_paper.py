from paper import size, step_day, risk_pct, can_propose, scorecard


def test_size_one_percent():
    assert size(50, 48, 54, 100000, 100000) == (400, "ok")


def test_size_notional_cap_20pct():
    assert size(100, 99.5, 101, 100000, 100000)[0] == 200


def test_leveraged_cap_10pct():
    assert size(50, 49, 52, 100000, 100000, leveraged=True)[0] == 200


def test_min_cash_kept():
    assert size(50, 49, 52, 100000, 15000)[0] == 100


def test_rejects_bad_rr():
    assert size(50, 49, 51, 100000, 100000)[0] == 0


def test_stop_first_same_day():
    pos = {"entry": 50, "stop": 49, "target": 52}
    assert step_day(pos, {"o": 50, "h": 53, "l": 48, "c": 50})[1] == "stop"


def test_gap_target():
    pos = {"entry": 50, "stop": 49, "target": 52}
    assert step_day(pos, {"o": 53, "h": 54, "l": 52.5, "c": 53}) == (53, "target (gap)")


def test_breakeven_then_time_stop():
    pos = {"entry": 50, "stop": 49, "target": 52, "days": 9}
    assert step_day(pos, {"o": 50, "h": 51.2, "l": 50.1, "c": 50.8}) == (50.8, "time stop")
    assert pos["stop"] == 50


def test_half_risk_in_drawdown():
    assert risk_pct(94000, 100000) == 0.005
    assert risk_pct(95000, 100000) == 0.01


def test_one_per_theme():
    l = {"cash": 95000, "equity_high": 100000, "positions": [{"symbol": "AMD", "shares": 10, "entry": 500, "theme": "semis"}]}
    assert can_propose(l, "semis")[0] is False
    assert can_propose(l, "banks")[0] is True


def test_scorecard():
    l = {"closed": [{"r": 2.0}, {"r": -1.0}, {"r": -1.0}, {"r": 2.0}]}
    assert scorecard(l) == {"trades": 4, "win_rate": 0.5, "expectancy_r": 0.5, "profit_factor": 2.0}
