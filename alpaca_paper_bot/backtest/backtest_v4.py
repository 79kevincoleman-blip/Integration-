"""v4 backtest: relative-strength momentum continuation (owner outline 2026-11-19).

"In stocks (or indexes/ETFs) showing relative strength or clear intermediate momentum, buy controlled
pullbacks or high-volume breakouts of consolidation, then exit at a predefined multiple of risk or when
the momentum structure breaks."

Scan:  universe = v2 stocks + index/sector ETFs. Relative strength = 63-day return minus SPY's 63-day return;
       must be > 0 and in the top RS_TOP. Intermediate momentum: close > 50d > 200d.
Buy:   pullback  - 3-8% off the 20-day high, pullback volume below the 50-day average (controlled),
                   low holds above the 50d MA, then close > prior day's high. Stop = pullback low - 0.1 ATR.
       breakout  - 15-30 day base < 12% wide, close > base high on > 1.5x 50-day volume. Stop = base midpoint.
       Skip if stop distance > 2.5 ATR(14).
Sell:  target = entry + R_MULT * risk; or close < 20-day MA (structure break); or stop; or 20 trading days.
Risk:  1% per trade, 20% max position, 5 positions, 2 per theme, 10% cash floor, cash earns BIL,
       next-open entries, 5 bps slippage per side, stop first when a bar hits stop and target.
Variants: R_MULT 2 or 3, with/without SPY > 200d regime filter. Reports full period + both halves.
"""
import argparse, json, math, os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from backtest import fetch_alpaca, load_csv_dir, sma, atr, UNIVERSE  # noqa: E402

SLIP = 0.0005
RISK, CAP, CASH_FLOOR, MAX_POS, PER_THEME = 0.01, 0.20, 0.10, 5, 2
RS_LB, RS_TOP, MAX_HOLD, MAX_STOP_ATR = 63, 10, 20, 2.5
BENCH, CASHETF = "SPY", "BIL"
ETFS = {"QQQ": "etf-index", "IWM": "etf-index", "XLK": "etf-tech", "SMH": "etf-tech", "XLE": "etf-energy",
        "XLF": "etf-fin", "XLV": "etf-health", "XLI": "etf-ind", "XLY": "etf-cons", "XLP": "etf-staples",
        "XLU": "etf-util"}
STOCKS = {s: t for t, ss in UNIVERSE.items() if t != "index-inverse" for s in ss}
NAMES = {**STOCKS, **ETFS}
VARIANTS = {"v4_2R": (2.0, False), "v4_3R": (3.0, False), "v4_2R_regime": (2.0, True), "v4_3R_regime": (3.0, True)}


def entry_signal(b, i):
    if i < 200:
        return None
    c = [x["c"] for x in b]
    s50, s200, a = sma(c, 50, i), sma(c, 200, i), atr(b, 14, i)
    if not (c[i] > s50 > s200) or not a:
        return None
    bar, prev = b[i], b[i - 1]
    vavg50 = sum(x["v"] for x in b[i - 50:i]) / 50
    # high-volume breakout of a 15-30 day consolidation
    for n in (30, 20, 15):
        hi, lo = max(x["h"] for x in b[i - n:i]), min(x["l"] for x in b[i - n:i])
        if (hi - lo) / lo < 0.12 and c[i] > hi and bar["v"] > 1.5 * vavg50:
            stop = (hi + lo) / 2
            return ("breakout", stop) if c[i] - stop <= MAX_STOP_ATR * a else None
    # controlled pullback
    hi20 = max(x["h"] for x in b[i - 20:i])
    k_hi = max(range(i - 20, i), key=lambda k: b[k]["h"])
    pull = b[k_hi + 1:i + 1]
    if len(pull) < 2:
        return None
    low = min(x["l"] for x in pull)
    dd = (hi20 - low) / hi20
    pull_vol = sum(x["v"] for x in pull[:-1]) / max(len(pull) - 1, 1)
    if 0.03 <= dd <= 0.08 and low > s50 and pull_vol < vavg50 and c[i] > prev["h"] and c[i] > bar["o"]:
        stop = low - 0.1 * a
        return ("pullback", stop) if c[i] - stop <= MAX_STOP_ATR * a else None
    return None


def run(data, days, r_mult, use_regime):
    idx = {s: {x["d"]: k for k, x in enumerate(v)} for s, v in data.items()}
    spy = data[BENCH]
    spy_c = [x["c"] for x in spy]
    cash, positions, trades, eq_hist, pending = 100000.0, [], [], [], []
    regime, prev_bil = False, None
    for d in days:
        kb = idx[CASHETF].get(d)
        if kb is not None:
            bil = data[CASHETF][kb]["c"]
            if prev_bil:
                cash *= bil / prev_bil
            prev_bil = bil
        for o in pending:
            k = idx[o["sym"]].get(d)
            if k is None or len(positions) >= MAX_POS or sum(p["theme"] == o["theme"] for p in positions) >= PER_THEME:
                continue
            px = data[o["sym"]][k]["o"] * (1 + SLIP)
            if px <= o["stop"]:
                continue
            rps = px - o["stop"]
            eq = cash + sum(p["qty"] * data[p["sym"]][p["k"]]["c"] for p in positions)
            qty = int(min(eq * RISK / rps, eq * CAP / px, max(cash - eq * CASH_FLOOR, 0) / px))
            if qty <= 0:
                continue
            cash -= qty * px
            positions.append({"sym": o["sym"], "theme": o["theme"], "setup": o["setup"], "entry": px, "stop": o["stop"],
                              "target": px + r_mult * rps, "rps": rps, "qty": qty, "days": 0, "d_in": d, "k": k})
        pending = []
        for p in list(positions):
            k = idx[p["sym"]].get(d)
            if k is None:
                continue
            p["k"] = k
            b = data[p["sym"]]
            bar = b[k]
            p["days"] += 1
            ex, why = None, None
            if bar["o"] <= p["stop"]:
                ex, why = bar["o"], "stop-gap"
            elif bar["l"] <= p["stop"]:
                ex, why = p["stop"], "stop"
            elif bar["o"] >= p["target"]:
                ex, why = bar["o"], "target-gap"
            elif bar["h"] >= p["target"]:
                ex, why = p["target"], "target"
            else:
                s20 = sma([x["c"] for x in b], 20, k)
                if s20 and bar["c"] < s20:
                    ex, why = bar["c"], "structure-break"
                elif p["days"] >= MAX_HOLD:
                    ex, why = bar["c"], "time"
            if ex is not None:
                ex *= (1 - SLIP)
                cash += p["qty"] * ex
                positions.remove(p)
                trades.append({"sym": p["sym"], "setup": p["setup"], "in": p["d_in"], "out": d, "days": p["days"],
                               "r": round((ex - p["entry"]) / p["rps"], 3), "why": why})
        eq_hist.append((d, cash + sum(p["qty"] * data[p["sym"]][p["k"]]["c"] for p in positions)))
        ks = idx[BENCH].get(d)
        if ks is None or ks < 200:
            continue
        m = sma(spy_c, 200, ks)
        regime = (spy_c[ks] > m * 0.98) if regime else (spy_c[ks] > m * 1.02)
        if use_regime and not regime:
            continue
        spy_ret = spy_c[ks] / spy_c[ks - RS_LB] - 1
        rs = []
        for s in NAMES:
            k = idx.get(s, {}).get(d)
            if k is None or k < RS_LB:
                continue
            r = data[s][k]["c"] / data[s][k - RS_LB]["c"] - 1 - spy_ret
            if r > 0:
                rs.append((r, s))
        rs.sort(reverse=True)
        held = {p["sym"] for p in positions}
        for _, s in rs[:RS_TOP]:
            if s in held:
                continue
            sig = entry_signal(data[s], idx[s][d])
            if sig:
                pending.append({"sym": s, "theme": NAMES[s], "setup": sig[0], "stop": sig[1]})
            if len(pending) >= 2:
                break
    return trades, eq_hist


def summarize(trades, eq_hist, data, t0, t1):
    tr = [t for t in trades if t0 <= t["in"] <= t1]
    vals = [v for d, v in eq_hist if t0 <= d <= t1]
    peak, mdd = vals[0], 0
    for v in vals:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak)
    yrs = len(vals) / 252
    rets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - mu) ** 2 for x in rets) / (len(rets) - 1))
    out = {"return_pct": round((vals[-1] / vals[0] - 1) * 100, 1),
           "cagr_pct": round(((vals[-1] / vals[0]) ** (1 / yrs) - 1) * 100, 2),
           "max_dd_pct": round(mdd * 100, 1), "sharpe": round(mu / sd * math.sqrt(252), 2) if sd else None}
    rs = [t["r"] for t in tr]
    if len(rs) > 1:
        n, m = len(rs), sum(rs) / len(rs)
        s = math.sqrt(sum((x - m) ** 2 for x in rs) / (n - 1))
        w, l = sum(x for x in rs if x > 0), -sum(x for x in rs if x < 0)
        out.update({"trades": n, "win_rate": round(sum(x > 0 for x in rs) / n, 3), "avg_r": round(m, 3),
                    "avg_r_95ci": [round(m - 1.96 * s / math.sqrt(n), 3), round(m + 1.96 * s / math.sqrt(n), 3)],
                    "profit_factor": round(w / l, 2) if l else None,
                    "by_setup": {k: round(sum(t["r"] for t in tr if t["setup"] == k) / max(1, sum(t["setup"] == k for t in tr)), 3)
                                 for k in ("pullback", "breakout")},
                    "by_exit": {k: sum(t["why"] == k for t in tr) for k in sorted({t["why"] for t in tr})}})
    return out


def spy_stats(data, t0, t1):
    c = [x["c"] for x in data[BENCH] if t0 <= x["d"] <= t1]
    peak, mdd = c[0], 0
    for x in c:
        peak = max(peak, x)
        mdd = max(mdd, (peak - x) / peak)
    yrs = len(c) / 252
    return {"return_pct": round((c[-1] / c[0] - 1) * 100, 1), "cagr_pct": round(((c[-1] / c[0]) ** (1 / yrs) - 1) * 100, 2),
            "max_dd_pct": round(mdd * 100, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="6")
    ap.add_argument("--csv-dir")
    ap.add_argument("--out", default="backtest_out")
    a = ap.parse_args()
    yrs = float(str(a.years).split(",")[-1])
    syms = sorted(set(NAMES) | {BENCH, CASHETF})
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=int(yrs * 365) + 330)
    data = load_csv_dir(a.csv_dir, syms) if a.csv_dir else fetch_alpaca(syms, start.isoformat(), end.isoformat())
    data = {s: sorted(v, key=lambda x: x["d"]) for s, v in data.items() if v}
    t0 = (end - timedelta(days=int(yrs * 365))).isoformat()
    bil_days = {y["d"] for y in data[CASHETF]}
    days = [x["d"] for x in data[BENCH] if x["d"] >= t0 and x["d"] in bil_days]
    mid = days[len(days) // 2]
    periods = {"full": (days[0], days[-1]), "first_half": (days[0], mid), "second_half": (mid, days[-1])}
    res = {"SPY": {k: spy_stats(data, *v) for k, v in periods.items()}}
    for name, (rm, reg) in VARIANTS.items():
        tr, eq = run(data, days, rm, reg)
        res[name] = {k: summarize(tr, eq, data, *v) for k, v in periods.items()}
    res["periods"] = {k: f"{v[0]} to {v[1]}" for k, v in periods.items()}
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "v4.json"), "w"), indent=1)
    print("SUMMARY_V4 " + json.dumps(res))
