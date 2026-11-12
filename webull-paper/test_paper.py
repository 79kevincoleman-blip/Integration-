from paper import size, step_bar


def test_size_one_percent():
    assert size(50, 49, 52, 100000, 100000) == (500, "ok")


def test_size_notional_cap():
    shares, _ = size(100, 99.9, 100.3, 100000, 100000)
    assert shares == 250


def test_size_rejects_bad_rr():
    assert size(50, 49, 51, 100000, 100000)[0] == 0


def test_stop_before_target_same_bar():
    pos = {"entry": 50, "stop": 49, "target": 52}
    assert step_bar(pos, {"o": 50, "h": 53, "l": 48, "c": 50})[1] == "stop"


def test_breakeven_after_1r():
    pos = {"entry": 50, "stop": 49, "target": 52}
    assert step_bar(pos, {"o": 50, "h": 51.2, "l": 50, "c": 51}) is None
    assert pos["stop"] == 50
