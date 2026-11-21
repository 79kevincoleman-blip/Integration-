"""v4.3 candidates: owner 2026-11-21 'make it take more trades and test it'.

One 10y data pull (v4.2 universe, ~309 names), several PRE-DECLARED variants, same engine/costs as v4:
next-open entries, 5 bps slippage per side, stop first when a bar hits stop and target, cash earns BIL.

  v41_ref   v4.1 thresholds (base<12%, vol 1.5x, RS top 10, 5 pos, 20% cap, 2/sector, 2 new/day)
  v42_live  what is live now (base<15%, vol 1.3x, RS top 100, 8 pos, 12.5% cap, 3/sector, 3 new/day)
  A_20dhigh close > prior 20-day high on >= 1.2x volume (no base-width test); stop = 10-day low
  B_shortbase v4.2 + 10-day bases allowed, vol 1.2x
  C_slots   v4.2 signals, 12 pos, 0.75% risk, 8.5% cap, 4/sector, 5 new/day
  D_fast    v4.2 + 2R target, 10-day max hold
  E_A_plus_C A_20dhigh signals with C_slots sizing
Exits for all: stop, target, close < 50d MA, or max hold. RS > SPY over 63 days and close > 50d > 200d for all.
Adoption rule (decided before the run): replace live only if trades/yr >= 1.5x v42_live AND avg R 95% CI low > 0
AND avg R > 0 in both halves AND 10y return > v4.1_ref. Otherwise stay on v4.2 and report.
"""
import argparse, json, math, os, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(__file__))
import strategy_v42 as s42  # noqa: E402  patches v4 universe
import backtest_v4 as v4  # noqa: E402
from backtest_v41 import sharpe  # noqa: E402

SLIP = v4.SLIP


def sig_base(widths, vol, wins):
    def f(b, i):
        if i < 200:
            return None
        c = [x["c"] for x in b]
        s50, s200, a = v4.sma(c, 50, i), v4.sma(c, 200, i), v4.atr(b, 14, i)
        if not (c[i] > s50 > s200) or not a:
            return None
        vavg = sum(x["v"] for x in b[i - 50:i]) / 50
        for n in wins:
            hi, lo = max(x["h"] for x in b[i - n:i]), min(x["l"] for x in b[i - n:i])
            if (hi - lo) / lo < widths and c[i] > hi and b[i]["v"] > vol * vavg:
                stop = (hi + lo) / 2
                return ("breakout", stop) if c[i] - stop <= v4.MAX_STOP_ATR * a else None
        return None
    return f


def sig_20dhigh(b, i):
    if i < 200:
        return None
    c = [x["c"] for x in b]
    s50, s200, a = v4.sma(c, 50, i), v4.sma(c, 200, i), v4.atr(b, 14, i)
    if not (c[i] > s50 > s200) or not a:
        return None
    vavg = sum(x["v"] for x in b[i - 50:i]) / 50
    if c[i] > max(x["h"] for x in b[i - 20:i]) and b[i]["v"] > 1.2 * vavg:
        stop = min(x["l"] for x in b[i - 10:i + 1])
        return ("breakout", stop) if c[i] - stop <= v4.MAX_STOP_ATR * a else None
    return None


BASE = dict(sig=sig_base(0.15, 1.3, (30, 20, 15)), rs_top=100, max_pos=8, cap=0.125, per=3, new=3,
            risk=0.01, r=3.0, hold=20)
VARIANTS = {
    "v41_ref": {**BASE, "sig": sig_base(0.12, 1.5, (30, 20, 15)), "rs_top": 10, "max_pos": 5, "cap": 0.20,
                "per": 2, "new": 2},
    "v42_live": BASE,
    "A_20dhigh": {**BASE, "sig": sig_20dhigh},
    "B_shortbase": {**BASE, "sig": sig_base(0.15, 1.2, (30, 20, 15, 10))},
    "C_slots": {**BASE, "max_pos": 12, "risk": 0.0075, "cap": 0.085, "per": 4, "new": 5},
    "D_fast": {**BASE, "r": 2.0, "hold": 10},
    "E_A_plus_C": {**BASE, "sig": sig_20dhigh, "max_pos": 12, "risk": 0.0075, "cap": 0.085, "per": 4, "new": 5},
}


def run(data, days, P):
    idx = {s: {x["d"]: k for k, x in enumerate(v)} for s, v in data.items()}
    closes = {s: [x["c"] for x in v] for s, v in data.items()}
    spy_c = closes[v4.BENCH]
    cash, pos, trades, eq_hist, pending, prev_bil = 100000.0, [], [], [], [], None
    for d in days:
        kb = idx[v4.CASHETF].get(d)
        if kb is not None:
            bil = data[v4.CASHETF][kb]["c"]
            if prev_bil:
                cash *= bil / prev_bil
            prev_bil = bil
        for o in pending:
            k = idx[o["sym"]].get(d)
            if k is None or len(pos) >= P["max_pos"] or sum(p["theme"] == o["theme"] for p in pos) >= P["per"]:
                continue
            px = data[o["sym"]][k]["o"] * (1 + SLIP)
            if px <= o["stop"]:
                continue
            rps = px - o["stop"]
            eq = cash + sum(p["qty"] * data[p["sym"]][p["k"]]["c"] for p in pos)
            qty = int(min(eq * P["risk"] / rps, eq * P["cap"] / px, max(cash - eq * v4.CASH_FLOOR, 0) / px))
            if qty <= 0:
                continue
            cash -= qty * px
            pos.append({"sym": o["sym"], "theme": o["theme"], "setup": "breakout", "entry": px, "stop": o["stop"],
                        "target": px + P["r"] * rps, "rps": rps, "qty": qty, "days": 0, "d_in": d, "k": k})
        pending = []
        for p in list(pos):
            k = idx[p["sym"]].get(d)
            if k is None:
                continue
            p["k"] = k
            bar = data[p["sym"]][k]
            p["days"] += 1
            ex = why = None
            if bar["o"] <= p["stop"]:
                ex, why = bar["o"], "stop-gap"
            elif bar["l"] <= p["stop"]:
                ex, why = p["stop"], "stop"
            elif bar["o"] >= p["target"]:
                ex, why = bar["o"], "target-gap"
            elif bar["h"] >= p["target"]:
                ex, why = p["target"], "target"
            else:
                m50 = v4.sma(closes[p["sym"]], 50, k)
                if m50 and bar["c"] < m50:
                    ex, why = bar["c"], "structure-break"
                elif p["days"] >= P["hold"]:
                    ex, why = bar["c"], "time"
            if ex is not None:
                ex *= 1 - SLIP
                cash += p["qty"] * ex
                pos.remove(p)
                trades.append({"sym": p["sym"], "setup": "breakout", "in": p["d_in"], "out": d, "days": p["days"],
                               "r": round((ex - p["entry"]) / p["rps"], 3), "why": why})
        eq_hist.append((d, cash + sum(p["qty"] * data[p["sym"]][p["k"]]["c"] for p in pos)))
        ks = idx[v4.BENCH].get(d)
        if ks is None or ks < 200:
            continue
        spy_ret = spy_c[ks] / spy_c[ks - v4.RS_LB] - 1
        rs = []
        for s in v4.NAMES:
            k = idx.get(s, {}).get(d)
            if k is None or k < v4.RS_LB:
                continue
            r = closes[s][k] / closes[s][k - v4.RS_LB] - 1 - spy_ret
            if r > 0:
                rs.append((r, s))
        rs.sort(reverse=True)
        held = {p["sym"] for p in pos}
        for _, s in rs[:P["rs_top"]]:
            if s in held:
                continue
            sig = P["sig"](data[s], idx[s][d])
            if sig:
                pending.append({"sym": s, "theme": v4.NAMES[s], "stop": sig[1]})
            if len(pending) >= P["new"]:
                break
    return trades, eq_hist


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--years", default="10"); ap.add_argument("--csv-dir"); ap.add_argument("--out", default="out")
    a = ap.parse_args()
    yrs = float(str(a.years).split(",")[-1])
    syms = sorted(set(v4.NAMES) | {v4.BENCH, v4.CASHETF})
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=int(yrs * 365) + 330)
    data = v4.load_csv_dir(a.csv_dir, syms) if a.csv_dir else v4.fetch_alpaca(syms, start.isoformat(), f"{end.isoformat()}T23:00:00Z")
    data = {s: sorted(v, key=lambda x: x["d"]) for s, v in data.items() if v}
    t0 = (end - timedelta(days=int(yrs * 365))).isoformat()
    bil = {y["d"] for y in data[v4.CASHETF]}
    days = [x["d"] for x in data[v4.BENCH] if x["d"] >= t0 and x["d"] in bil]
    mid = days[len(days) // 2]
    PER = {"full": (days[0], days[-1]), "first_half": (days[0], mid), "second_half": (mid, days[-1])}
    spy_eq = [(x["d"], x["c"]) for x in data[v4.BENCH] if x["d"] in set(days)]
    res = {"periods": {k: f"{v[0]} to {v[1]}" for k, v in PER.items()}, "symbols_loaded": len(data),
           "SPY": {k: {**v4.spy_stats(data, *v), "sharpe": sharpe(spy_eq, *v)} for k, v in PER.items()}}
    all_trades = {}
    for name, P in VARIANTS.items():
        tr, eq = run(data, days, P)
        all_trades[name] = tr
        res[name] = {k: {**v4.summarize(tr, eq, data, *v), "sharpe": sharpe(eq, *v)} for k, v in PER.items()}
        res[name]["full"]["trades_per_year"] = round(len(tr) / yrs, 1)
        res[name]["end_equity"] = round(eq[-1][1])
    base_tpy = res["v42_live"]["full"]["trades_per_year"]
    ref_ret = res["v41_ref"]["full"]["return_pct"]
    adopt = {}
    for name in VARIANTS:
        if name in ("v41_ref", "v42_live"):
            continue
        f, h1, h2 = res[name]["full"], res[name]["first_half"], res[name]["second_half"]
        adopt[name] = {"more_trades": f["trades_per_year"] >= 1.5 * base_tpy,
                       "ci_low_pos": f.get("avg_r_95ci", [-1])[0] > 0,
                       "both_halves_pos": h1.get("avg_r", -1) > 0 and h2.get("avg_r", -1) > 0,
                       "beats_v41_return": f["return_pct"] > ref_ret}
        adopt[name]["PASS"] = all(adopt[name].values())
    res["adoption"] = adopt
    os.makedirs(a.out, exist_ok=True)
    json.dump({"summary": res, "trades": all_trades}, open(os.path.join(a.out, "v43.json"), "w"), indent=1)
    print("SUMMARY_V43 " + json.dumps(res))
