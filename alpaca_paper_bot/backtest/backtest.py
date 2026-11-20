"""Backtest of the v2 swing rules on daily bars.

Runs in GitHub Actions (keys from repo secrets) or locally with --csv-dir for offline data.
Rules mirror RULES.md: 1% risk, 20% notional cap (10% leveraged), max 5 positions,
1 per theme, 10% cash floor, 2R target, breakeven at +1R, 10-day time stop,
stop-first when a bar hits both. Signals on day t's close, entry at day t+1 open.
Costs: 5 bps slippage per side.
"""
import argparse, csv, json, math, os, sys, urllib.request, urllib.parse
from datetime import date, timedelta

UNIVERSE = {
    # theme: symbols
    "semis": ["NVDA", "AMD", "AVGO", "MU", "QCOM", "INTC"],
    "megatech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
    "software": ["CRM", "ORCL", "ADBE", "NOW"],
    "banks": ["JPM", "BAC", "GS", "WFC"],
    "energy": ["XOM", "CVX", "COP", "SLB"],
    "health": ["UNH", "LLY", "JNJ", "ABBV", "PFE"],
    "industrial": ["CAT", "GE", "HON", "DE"],
    "consumer": ["COST", "WMT", "HD", "MCD", "NKE"],
    "auto_ev": ["TSLA", "RIVN", "F"],
    "fintech": ["NU", "SOFI", "PYPL"],
    "media": ["SNAP", "DIS"],
    "index-inverse": ["SH", "PSQ"],
}
LEVERAGED = {"SOXS", "SQQQ", "SPXS"}
BENCH = "SPY"
SLIP = 0.0005
SETUPS = {"pullback", "base-breakout", "inverse-breakdown"}  # "reversal" trial FAILED 11-19; opt in via request.json "setups"
RISK, CAP, CAP_LEV, CASH_FLOOR, MAX_POS, RR, TIME_STOP = 0.01, 0.20, 0.10, 0.10, 5, 2.0, 10


# ---------------- data ----------------
def fetch_alpaca(symbols, start, end):
    if "T" not in end:
        end = end + "T00:00:00Z"  # explicit UTC; a bare date can count as "recent SIP data" and get a 403
    key = os.environ["ALPACA_KEY_ID"].strip()
    sec = os.environ["ALPACA_SECRET_KEY"].strip()
    out = {s: [] for s in symbols}
    for feed in ("sip", "iex"):
        token, ok = None, True
        while True:
            q = {"symbols": ",".join(symbols), "timeframe": "1Day", "start": start, "end": end,
                 "limit": 10000, "adjustment": "all", "feed": feed}
            if token:
                q["page_token"] = token
            req = urllib.request.Request("https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(q),
                                         headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    j = json.loads(r.read())
            except urllib.error.HTTPError as e:
                print(f"feed {feed} error {e.code}: {e.read()[:200]}", file=sys.stderr)
                ok = False
                break
            for s, bars in (j.get("bars") or {}).items():
                out[s] += [{"d": b["t"][:10], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]} for b in bars]
            token = j.get("next_page_token")
            if not token:
                break
        if ok and any(out.values()):
            print(f"data feed: {feed}", file=sys.stderr)
            return out
        out = {s: [] for s in symbols}
    raise SystemExit("could not fetch bars")


def load_csv_dir(path, symbols):
    out = {}
    for s in symbols:
        f = os.path.join(path, s + ".csv")
        if os.path.exists(f):
            with open(f) as fh:
                out[s] = [{"d": r["d"], **{k: float(r[k]) for k in "ohlcv"}} for r in csv.DictReader(fh)]
    return out


# ---------------- indicators ----------------
def sma(xs, n, i):
    return sum(xs[i - n + 1:i + 1]) / n if i >= n - 1 else None


def atr(bars, n, i):
    if i < n:
        return None
    trs = [max(bars[k]["h"] - bars[k]["l"], abs(bars[k]["h"] - bars[k - 1]["c"]), abs(bars[k]["l"] - bars[k - 1]["c"]))
           for k in range(i - n + 1, i + 1)]
    return sum(trs) / n


def rsi(c, n, i):
    if i < n:
        return None
    g = sum(max(c[k] - c[k - 1], 0) for k in range(i - n + 1, i + 1))
    l = sum(max(c[k - 1] - c[k], 0) for k in range(i - n + 1, i + 1))
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def reversal(b, i, s50, a):
    """TEMPORARY trial (owner, 2026-11-19): downtrend -> lowest low -> confirmed reversal.
    Liquid universe only (price > $5). Mirrors webull_strategy.py on the Webull branch."""
    c = [x["c"] for x in b]
    bar, prev = b[i], b[i - 1]
    if c[i] <= 5 or a is None:
        return None
    hi60 = max(x["h"] for x in b[i - 60:i])
    lo60 = min(x["l"] for x in b[i - 60:i + 1])
    if not (prev["c"] < s50 and (hi60 - lo60) / hi60 >= 0.15):   # was in a downtrend, 15%+ off the high
        return None
    vavg = sum(x["v"] for x in b[i - 50:i]) / 50
    sig = c[i] > prev["h"] or (rsi(c, 14, i - 1) or 50) < 30 <= (rsi(c, 14, i) or 50) \
        or (c[i] > prev["c"] and bar["v"] >= 1.5 * vavg)
    if c[i] <= lo60 * 1.03 and sig:                              # A: at the lowest low + 1 signal
        return ("reversal", lo60 - 0.1 * a)
    w = b[i - 20:i + 1]
    k = min(range(len(w)), key=lambda j: w[j]["l"])
    after = w[k + 1:-1]
    if len(after) >= 3:                                          # B: takeoff
        bounce = max(x["h"] for x in after)
        hl = min(x["l"] for x in after)
        if hl > w[k]["l"] and c[i] > bounce and bar["v"] >= 1.5 * vavg:
            return ("reversal", hl - 0.1 * a)
    return None


# ---------------- signals (evaluated at close of bar i) ----------------
def signal(sym, theme, b, i, spy, spy_i):
    c = [x["c"] for x in b]
    if i < 200:
        return None
    s20, s50, s200, a = sma(c, 20, i), sma(c, 50, i), sma(c, 200, i), atr(b, 14, i)
    bar, prev = b[i], b[i - 1]
    if theme == "index-inverse":
        if spy_i is None or spy_i < 50:
            return None
        sc = [x["c"] for x in spy]
        spy20, spy50 = sma(sc, 20, spy_i), sma(sc, 50, spy_i)
        # market downtrend + SPY breaks prior-day low  => inverse ETF breaks prior-day high
        if "inverse-breakdown" in SETUPS and sc[spy_i] < spy20 < spy50 and spy[spy_i]["l"] < spy[spy_i - 1]["l"] and bar["c"] > prev["h"]:
            stop = min(x["l"] for x in b[i - 4:i + 1]) - 0.1 * a
            return ("inverse-breakdown", stop)
        return None
    if not (c[i] > s50 > s200):
        return reversal(b, i, s50, a) if "reversal" in SETUPS else None
    hi20 = max(x["h"] for x in b[i - 20:i])
    lo20 = min(x["l"] for x in b[i - 20:i])
    # base breakout
    width = (hi20 - lo20) / lo20
    vavg = sum(x["v"] for x in b[i - 50:i]) / 50
    if "base-breakout" in SETUPS and width < 0.12 and c[i] > hi20 and bar["v"] > 1.5 * vavg:
        return ("base-breakout", (hi20 + lo20) / 2)
    # pullback in uptrend: pulled back 3-8% from 20d high, touched near the 20d MA, green day closing above prior high
    recent_low = min(x["l"] for x in b[i - 4:i + 1])
    dd = (hi20 - recent_low) / hi20
    if "pullback" in SETUPS and 0.03 <= dd <= 0.08 and recent_low <= s20 * 1.01 and c[i] > bar["o"] and c[i] > prev["h"]:
        return ("pullback", recent_low - 0.1 * a)
    return None


# ---------------- portfolio simulation ----------------
def run(data, start_trade):
    theme_of = {s: t for t, ss in UNIVERSE.items() for s in ss}
    idx = {s: {x["d"]: k for k, x in enumerate(bars)} for s, bars in data.items()}
    days = sorted({x["d"] for x in data[BENCH] if x["d"] >= start_trade})
    cash, eq_hist, positions, trades, pending = 100000.0, [], [], [], []
    peak = 100000.0

    def equity(d):
        v = cash
        for p in positions:
            k = idx[p["sym"]].get(d)
            v += p["qty"] * (data[p["sym"]][k]["c"] if k is not None else p["entry"])
        return v

    for d in days:
        # 1) fill pending entries at today's open
        for o in pending:
            k = idx[o["sym"]].get(d)
            if k is None or len(positions) >= MAX_POS or any(p["theme"] == o["theme"] for p in positions):
                continue
            px = data[o["sym"]][k]["o"] * (1 + SLIP)
            if px <= o["stop"]:
                continue
            rps = px - o["stop"]
            target = px + RR * rps
            eq = equity(d)
            risk = RISK / 2 if eq <= peak * 0.94 else RISK
            cap = CAP_LEV if o["sym"] in LEVERAGED else CAP
            qty = int(min(eq * risk / rps, eq * cap / px, max(cash - eq * CASH_FLOOR, 0) / px))
            if qty <= 0:
                continue
            cash -= qty * px
            positions.append({"sym": o["sym"], "theme": o["theme"], "setup": o["setup"], "entry": px, "stop": o["stop"],
                              "target": target, "rps": rps, "qty": qty, "days": 0, "be": False, "d_in": d})
        pending = []
        # 2) manage open positions on today's bar
        for p in list(positions):
            k = idx[p["sym"]].get(d)
            if k is None:
                continue
            bar = data[p["sym"]][k]
            p["days"] += 1
            exit_px, why = None, None
            if bar["o"] <= p["stop"]:
                exit_px, why = bar["o"], "stop-gap"
            elif bar["l"] <= p["stop"]:
                exit_px, why = p["stop"], "stop" if not p["be"] else "breakeven"
            elif bar["o"] >= p["target"]:
                exit_px, why = bar["o"], "target-gap"
            elif bar["h"] >= p["target"]:
                exit_px, why = p["target"], "target"
            else:
                if not p["be"] and bar["h"] >= p["entry"] + p["rps"]:
                    p["be"], p["stop"] = True, p["entry"]
                if p["days"] >= TIME_STOP:
                    exit_px, why = bar["c"], "time"
            if exit_px is not None:
                exit_px *= (1 - SLIP)
                cash += p["qty"] * exit_px
                positions.remove(p)
                trades.append({"sym": p["sym"], "setup": p["setup"], "in": p["d_in"], "out": d, "entry": round(p["entry"], 2),
                               "exit": round(exit_px, 2), "qty": p["qty"], "pnl": round((exit_px - p["entry"]) * p["qty"], 2),
                               "r": round((exit_px - p["entry"]) / p["rps"], 3), "why": why})
        eq = equity(d)
        peak = max(peak, eq)
        eq_hist.append((d, eq))
        # 3) signals at today's close -> entries tomorrow
        spy_i = idx[BENCH].get(d)
        cands = []
        for s, bars in data.items():
            if s == BENCH or s not in theme_of:
                continue
            k = idx[s].get(d)
            if k is None or any(p["sym"] == s for p in positions):
                continue
            sig = signal(s, theme_of[s], bars, k, data[BENCH], spy_i)
            if sig:
                cands.append({"sym": s, "theme": theme_of[s], "setup": sig[0], "stop": sig[1]})
        pending = cands[:2]  # max 2 new orders per day, like the live scan
    return trades, eq_hist


def stats(trades, eq_hist, data):
    rs = [t["r"] for t in trades]
    n = len(rs)
    out = {"trades": n}
    if n:
        mean = sum(rs) / n
        sd = math.sqrt(sum((x - mean) ** 2 for x in rs) / (n - 1)) if n > 1 else 0
        wins, losses = sum(x for x in rs if x > 0), -sum(x for x in rs if x < 0)
        out.update({"win_rate": round(sum(x > 0 for x in rs) / n, 3), "expectancy_r": round(mean, 3),
                    "expectancy_r_95ci": [round(mean - 1.96 * sd / math.sqrt(n), 3), round(mean + 1.96 * sd / math.sqrt(n), 3)],
                    "profit_factor": round(wins / losses, 2) if losses else None,
                    "by_setup": {}})
        for s in sorted({t["setup"] for t in trades}):
            sr = [t["r"] for t in trades if t["setup"] == s]
            out["by_setup"][s] = {"trades": len(sr), "expectancy_r": round(sum(sr) / len(sr), 3),
                                  "win_rate": round(sum(x > 0 for x in sr) / len(sr), 3)}
    eqs = [e for _, e in eq_hist]
    peak, mdd = eqs[0], 0
    for e in eqs:
        peak = max(peak, e)
        mdd = max(mdd, (peak - e) / peak)
    yrs = len(eqs) / 252
    out.update({"start": eq_hist[0][0], "end": eq_hist[-1][0], "final_equity": round(eqs[-1], 2),
                "total_return_pct": round((eqs[-1] / 100000 - 1) * 100, 2),
                "cagr_pct": round(((eqs[-1] / 100000) ** (1 / yrs) - 1) * 100, 2) if yrs > 0 else None,
                "max_drawdown_pct": round(mdd * 100, 2)})
    spy = [x for x in data[BENCH] if eq_hist[0][0] <= x["d"] <= eq_hist[-1][0]]
    sp, smdd = spy[0]["c"], 0
    for x in spy:
        sp = max(sp, x["c"])
        smdd = max(smdd, (sp - x["c"]) / sp)
    out["spy_buy_hold"] = {"total_return_pct": round((spy[-1]["c"] / spy[0]["c"] - 1) * 100, 2),
                           "cagr_pct": round(((spy[-1]["c"] / spy[0]["c"]) ** (1 / yrs) - 1) * 100, 2) if yrs > 0 else None,
                           "max_drawdown_pct": round(smdd * 100, 2)}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=3)
    ap.add_argument("--csv-dir")
    ap.add_argument("--out", default="backtest_out")
    ap.add_argument("--request", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "request.json"))
    a = ap.parse_args()
    if os.path.exists(a.request):
        req = json.load(open(a.request))
        if req.get("setups"):
            SETUPS = set(req["setups"])
    print(f"setups: {sorted(SETUPS)}", file=sys.stderr)
    syms = sorted({s for ss in UNIVERSE.values() for s in ss} | {BENCH})
    end = date.today()
    trade_start = end - timedelta(days=int(a.years * 365))
    data_start = trade_start - timedelta(days=330)  # warm-up for 200-day MA
    data = load_csv_dir(a.csv_dir, syms) if a.csv_dir else fetch_alpaca(syms, data_start.isoformat(), end.isoformat())
    data = {s: sorted(v, key=lambda x: x["d"]) for s, v in data.items() if v}
    trades, eq = run(data, trade_start.isoformat())
    res = stats(trades, eq, data)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "trades.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(trades[0].keys()) if trades else ["none"])
        w.writeheader()
        w.writerows(trades)
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("SUMMARY " + json.dumps(res))
