import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backtest"))
import backtest as bt


def bars_down_then_reverse():
    b = []
    for k in range(80):                       # steady downtrend 30 -> ~18
        c = 30 - k * 0.15
        b.append({"d": f"d{k}", "o": c + 0.05, "h": c + 0.2, "l": c - 0.2, "c": c, "v": 1000})
    last = b[-1]
    b.append({"d": "rev", "o": last["c"], "h": last["h"] + 0.5, "l": last["l"], "c": last["h"] + 0.05, "v": 2000})
    return b


def test_reversal_fires_at_low_with_signal():
    b = bars_down_then_reverse()
    i = len(b) - 1
    c = [x["c"] for x in b]
    sig = bt.reversal(b, i, bt.sma(c, 50, i), bt.atr(b, 14, i))
    assert sig and sig[0] == "reversal" and sig[1] < b[i]["l"]


def test_no_signal_while_still_falling():
    b = bars_down_then_reverse()[:-1]
    i = len(b) - 1
    c = [x["c"] for x in b]
    assert bt.reversal(b, i, bt.sma(c, 50, i), bt.atr(b, 14, i)) is None


def test_penny_stock_excluded():
    b = [{**x, **{k: x[k] / 10 for k in "ohlc"}} for x in bars_down_then_reverse()]
    i = len(b) - 1
    c = [x["c"] for x in b]
    assert bt.reversal(b, i, bt.sma(c, 50, i), bt.atr(b, 14, i)) is None
