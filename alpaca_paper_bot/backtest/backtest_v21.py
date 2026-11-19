"""v2.1 backtest: v2 swing setups, repaired.

Changes vs v2 (each fixes a measured weakness):
  1. Market regime filter: new longs only while SPY > 200-day MA (2% band, same as v3-B).
  2. Momentum ranking: only the top-N stocks by 126-day return are eligible; candidates ranked by it.
  3. Let winners run: no fixed 2R target, no breakeven stop. Exit on a 3x ATR chandelier trailing stop
     (from the highest close) or a close below the 50-day MA, or after MAX_HOLD days.
  4. Idle cash earns the T-bill rate (BIL daily return).
  5. Inverse ETFs dropped (they lost money in v2 and v3).
Kept: 1% risk per trade, 20% max position, max 5 positions, 10% cash floor, signal at close -> enter next open,
5 bps slippage per side, stop checked before anything else on each bar.

Reports the full period plus two halves, so one lucky stretch can't carry the result.
"""
import argparse, json, math, os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from backtest import fetch_alpaca, load_csv_dir, sma, atr, UNIVERSE  # noqa: E402

SLIP = 0.0005
RISK, CAP, CASH_FLOOR, MAX_POS, PER_THEME = 0.01, 0.20, 0.10, 5, 2
TOP_N, MOM_LB, TRAIL_ATR, MAX_HOLD = 10, 126, 3.0, 60
BENCH, CASHETF = "SPY", "BIL"
STOCKS = {s: t for t, ss in UNIVERSE.items() if t != "index-inverse" for s in ss}


def regime_on(spy_c, i, state):
    m = sma(spy_c, 200, i)
    if m is None:
        return False
    if state and spy_c[i] < m * 0.98:
        return False
    if not state and spy_c[i] > m * 1.02:
        return True
    return state


def entry_signal(b, i):
    """Same two v2 setups, evaluated at close of bar i. Returns (setup, initial_stop) or None."""
    c = [x["c"] for x in b]
    if i < 200:
        return None
    s20, s50, s200, a = sma(c, 20, i), sma(c, 50, i), sma(c, 200, i), atr(b, 14, i)
    if not (c[i] > s50 > s200):
        return None
    bar, prev = b[i], b[i - 1]
    hi20 = max(x["h"] for x in b[i - 20:i])
    lo20 = min(x["l"] for x in b[i - 20:i])
    vavg = sum(x["v"] for x in b[i - 50:i]) / 50
    if (hi20 - lo20) / lo20 < 0.12 and c[i] > hi20 and bar["v"] > 1.5 * vavg:
        return ("base-breakout", max((hi20 + lo20) / 2, c[i] - 3 * a))
    recent_low = min(x["l"] for x in b[i - 4:i + 1])
    dd = (hi20 - recent_low) / hi20
    if 0.03 <= dd <= 0.08 and recent_low <= s20 * 1.01 and c[i] > bar["o"] and c[i] > prev["h"]:
        return ("pullback", recent_low - 0.1 * a)
    return None


def run(data, days):
    idx = {s: {x["d"]: k for k, x in enumerate(v)} for s, v in data.items()}
    spy_c = [x["c"] for x in data[BENCH]]
    cash, positions, trades, eq_hist, pending = 100000.0, [], [], [], []
    regime, prev_bil = False, None
    for d in days:
        # idle cash earns T-bills
        kb = idx[CASHETF].get(d)
        if kb is not None:
            bil = data[CASHETF][kb]["c"]
            if prev_bil:
                cash *= bil / prev_bil
            prev_bil = bil
        # entries at today's open
        for o in pending:
            k = idx[o["sym"]].get(d)
            if k is None or len(positions) >= MAX_POS:
                continue
            if sum(p["theme"] == o["theme"] for p in positions) >= PER_THEME:
                continue
            px = data[o["sym"]][k]["o"] * (1 + SLIP)
            if px <= o["stop"]:
                continue
            rps = px - o["stop"]
            eq = cash + sum(p["qty"] * data[p["sym"]][idx[p["sym"]].get(d, p["k_last"])]["o"] for p in positions)
            qty = int(min(eq * RISK / rps, eq * CAP / px, max(cash - eq * CASH_FLOOR, 0) / px))
            if qty <= 0:
                continue
            cash -= qty * px
            positions.append({"sym": o["sym"], "theme": o["theme"], "setup": o["setup"], "entry": px, "stop": o["stop"],
                              "rps": rps, "qty": qty, "days": 0, "hi": px, "d_in": d, "k_last": k})
        pending = []
        # manage positions
        for p in list(positions):
            k = idx[p["sym"]].get(d)
            if k is None:
                continue
            p["k_last"] = k
            b = data[p["sym"]]
            bar = b[k]
            p["days"] += 1
            exit_px, why = None, None
            if bar["o"] <= p["stop"]:
                exit_px, why = bar["o"], "stop-gap"
            elif bar["l"] <= p["stop"]:
                exit_px, why = p["stop"], "trail" if p["stop"] > p["entry"] - p["rps"] + 1e-9 else "stop"
            else:
                c = [x["c"] for x in b]
                s50 = sma(c, 50, k)
                if s50 and bar["c"] < s50:
                    exit_px, why = bar["c"], "below-50d"
                elif p["days"] >= MAX_HOLD:
                    exit_px, why = bar["c"], "time"
                else:
                    p["hi"] = max(p["hi"], bar["c"])
                    a = atr(b, 14, k)
                    if a:
                        p["stop"] = max(p["stop"], p["hi"] - TRAIL_ATR * a)
            if exit_px is not None:
                exit_px *= (1 - SLIP)
                cash += p["qty"] * exit_px
                positions.remove(p)
                trades.append({"sym": p["sym"], "setup": p["setup"], "in": p["d_in"], "out": d, "days": p["days"],
                               "r": round((exit_px - p["entry"]) / p["rps"], 3),
                               "pnl": round((exit_px - p["entry"]) * p["qty"], 2), "why": why})
        eq = cash + sum(p["qty"] * data[p["sym"]][p["k_last"]]["c"] for p in positions)
        eq_hist.append((d, eq))
        # signals at close
        ks = idx[BENCH].get(d)
        regime = regime_on(spy_c, ks, regime) if ks is not None else regime
        if not regime:
            continue
        mom = []
        for s in STOCKS:
            k = idx.get(s, {}).get(d)
            if k is None or k < MOM_LB:
                continue
            mom.append((data[s][k]["c"] / data[s][k - MOM_LB]["c"] - 1, s))
        mom.sort(reverse=True)
        held = {p["sym"] for p in positions}
        for r, s in mom[:TOP_N]:
            if r <= 0 or s in held:
                continue
            sig = entry_signal(data[s], idx[s][d])
            if sig:
                pending.append({"sym": s, "theme": STOCKS[s], "setup": sig[0], "stop": sig[1]})
            if len(pending) >= 2:
                break
    return trades, eq_hist


def summarize(trades, eq_hist, data, t0, t1):
    tr = [t for t in trades if t0 <= t["in"] <= t1]
    eq = [(d, v) for d, v in eq_hist if t0 <= d <= t1]
    vals = [v for _, v in eq]
    peak, mdd = vals[0], 0
    for v in vals:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak)
    yrs = len(vals) / 252
    rets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - mu) ** 2 for x in rets) / (len(rets) - 1))
    spy = [x["c"] for x in data[BENCH] if t0 <= x["d"] <= t1]
    sp, smdd = spy[0], 0
    for x in spy:
        sp = max(sp, x)
        smdd = max(smdd, (sp - x) / sp)
    out = {"period": f"{eq[0][0]} to {eq[-1][0]}",
           "strategy": {"return_pct": round((vals[-1] / vals[0] - 1) * 100, 1),
                        "cagr_pct": round(((vals[-1] / vals[0]) ** (1 / yrs) - 1) * 100, 2),
                        "max_dd_pct": round(mdd * 100, 1), "sharpe": round(mu / sd * math.sqrt(252), 2)},
           "spy": {"return_pct": round((spy[-1] / spy[0] - 1) * 100, 1),
                   "cagr_pct": round(((spy[-1] / spy[0]) ** (1 / yrs) - 1) * 100, 2), "max_dd_pct": round(smdd * 100, 1)}}
    rs = [t["r"] for t in tr]
    if rs:
        n, m = len(rs), sum(rs) / len(rs)
        s = math.sqrt(sum((x - m) ** 2 for x in rs) / (n - 1)) if n > 1 else 0
        w, l = sum(x for x in rs if x > 0), -sum(x for x in rs if x < 0)
        out["trades"] = {"n": n, "win_rate": round(sum(x > 0 for x in rs) / n, 3), "avg_r": round(m, 3),
                         "avg_r_95ci": [round(m - 1.96 * s / math.sqrt(n), 3), round(m + 1.96 * s / math.sqrt(n), 3)],
                         "profit_factor": round(w / l, 2) if l else None,
                         "avg_days": round(sum(t["days"] for t in tr) / n, 1),
                         "best_r": max(rs), "worst_r": min(rs),
                         "by_exit": {k: sum(t["why"] == k for t in tr) for k in sorted({t["why"] for t in tr})}}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="6")
    ap.add_argument("--csv-dir")
    ap.add_argument("--out", default="backtest_out")
    a = ap.parse_args()
    yrs = float(str(a.years).split(",")[-1])
    syms = sorted(set(STOCKS) | {BENCH, CASHETF})
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=int(yrs * 365) + 330)
    data = load_csv_dir(a.csv_dir, syms) if a.csv_dir else fetch_alpaca(syms, start.isoformat(), end.isoformat())
    data = {s: sorted(v, key=lambda x: x["d"]) for s, v in data.items() if v}
    t0 = (end - timedelta(days=int(yrs * 365))).isoformat()
    days = [x["d"] for x in data[BENCH] if x["d"] >= t0 and x["d"] in {y["d"] for y in data[CASHETF]}]
    trades, eq = run(data, days)
    mid = days[len(days) // 2]
    res = {"full": summarize(trades, eq, data, days[0], days[-1]),
           "first_half": summarize(trades, eq, data, days[0], mid),
           "second_half": summarize(trades, eq, data, mid, days[-1])}
    os.makedirs(a.out, exist_ok=True)
    json.dump({"summary": res, "trades": trades}, open(os.path.join(a.out, "v21.json"), "w"), indent=1)
    print("SUMMARY_V21 " + json.dumps(res))
