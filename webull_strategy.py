"""Webull reversal strategy (webull-strategy.md). Pure math on bar data, no network, no orders."""

LOW_ZONE_PCT = 0.03
VOLATILE_ATR_PCT = 0.04
VOLUME_MULT = 1.5


def rsi(closes, n=14):
    if len(closes) <= n:
        return None
    gains = losses = 0.0
    for a, b in zip(closes[-n - 1:-1], closes[-n:]):
        d = b - a
        gains += max(d, 0)
        losses += max(-d, 0)
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return 100 - 100 / (1 + rs)


def timeframe(atr_pct, has_news=False):
    return "INTRADAY" if atr_pct >= VOLATILE_ATR_PCT or has_news else "DAILY"


def reversal_signals(bars, avg_volume):
    """bars: list of dicts with high, low, close, volume (oldest first). Returns list of signal names."""
    last, prev = bars[-1], bars[-2]
    closes = [b["close"] for b in bars]
    sig = []
    if last["close"] > prev["high"]:
        sig.append("close_above_prior_high")
    r_now, r_prev = rsi(closes), rsi(closes[:-1])
    if r_now is not None and r_prev is not None and r_prev < 30 <= r_now:
        sig.append("rsi_back_above_30")
    if last["close"] > prev["close"] and last["volume"] >= VOLUME_MULT * avg_volume:
        sig.append("up_on_volume")
    return sig


def at_lowest_low(bars):
    lowest = min(b["low"] for b in bars)
    return bars[-1]["close"] <= lowest * (1 + LOW_ZONE_PCT), lowest


def takeoff(bars, avg_volume, lookback=20):
    """Higher low that holds, then a break above the last bounce high on volume."""
    w = bars[-lookback:]
    i_low = min(range(len(w)), key=lambda i: w[i]["low"])
    after = w[i_low + 1:-1]
    if len(after) < 3:
        return False
    bounce_high = max(b["high"] for b in after)
    higher_low = min(b["low"] for b in after) > w[i_low]["low"]
    last = w[-1]
    return higher_low and last["close"] > bounce_high and last["volume"] >= VOLUME_MULT * avg_volume


def evaluate(bars, avg_volume):
    """Returns ('BUY_LOW'|'BUY_TAKEOFF'|'WATCH', signals, lowest_low)."""
    low_zone, lowest = at_lowest_low(bars)
    sig = reversal_signals(bars, avg_volume)
    if low_zone and len(sig) >= 1:
        return "BUY_LOW", sig, lowest
    if takeoff(bars, avg_volume):
        return "BUY_TAKEOFF", sig, lowest
    return "WATCH", sig, lowest


def plan(entry, lowest_low, account_value, stop_buffer=0.01):
    """Stop just under the lowest low, target 2x risk, size to 2% account risk."""
    stop = round(lowest_low * (1 - stop_buffer), 2)
    risk = entry - stop
    if risk <= 0:
        return None
    target = round(entry + 2 * risk, 2)
    shares = round(account_value * 0.02 / risk, 4)
    return {"entry": entry, "stop": stop, "target": target, "shares": shares}
