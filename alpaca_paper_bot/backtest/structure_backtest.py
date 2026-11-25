"""STRUCTURE (owner spec 2026-11-25, from the Webull risk-sheet scan). PRE-REGISTERED before the first run.

Owner: "any low price comparable to the history of that particular stock. Then see if it slows down or if
there's a higher low and another higher low with a higher high and another higher high. Compare that to the
history and check the name's reputation."

Daily bars, decided at the close of day t, entry at the open of day t+1.
 1 LOW VS OWN HISTORY  close <= 1.20 x the stock's trailing 252-day low.
 2 FALL SLOWING        20-day close slope now > the prior 20-day slope (S2/S1 variants).
 3 STRUCTURE           swing pivots = 3 bars each side, usable only 3 bars after they form (no look-ahead),
                       within the last 90 bars. S2 = 2 higher lows AND 2 higher highs. S1 = 1 HL + 1 HH.
                       First day the stage appears only (no repeat entries while it persists).
 4 STOP                last confirmed swing low - 0.1 ATR(14). Skip if the stop is more than 3 ATR away.
 5 EXIT                target 2R; stop to breakeven at +1R; time stop 20 trading days; stop first if a bar hits both.
 Risk 1% of equity, max 12 positions (owner's 12), notional cap 15%, cash floor 10%, max 3 new/day.
 Costs 5 bps per side. Reputation (news/analysts) cannot be backtested: it is a manual check before any live GO.

Variants: S2 (rules 1-3 with S2), S2_noslow (S2 without rule 2), S1 (rules 1-3 with S1),
          NEAR (baseline: rule 1 + a close above the prior day's high, no structure).
PASS (decided before the run) for a variant: avg R 95% CI lower bound > 0, avg R > 0 in both halves,
total return > 0 after costs, AND it must beat NEAR on avg R (else the structure adds nothing).
SPY buy-and-hold is reported as the benchmark the owner's rule #6 compares against.
"""
import argparse, json, math, os, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import fetch_alpaca, load_csv_dir

UNIVERSE = sorted(set((
    "NU MARA SKYD BAC SAN F NKE HLN ERIC JD BCS NWG PDD FCX BSX CARR ENB O GSK TFC BN WFC C SCHW COF AXP MS TJX "
    "NEM RIO KKR DASH PCAR BKR DHI CBRE EQT PUK MCHP META AVGO KLAC INTU CI VST CEG TTWO SCCO WPM "
    "NVDA AMD MU QCOM INTC AAPL MSFT GOOGL AMZN CRM ORCL ADBE JPM GS XOM CVX COP SLB UNH LLY JNJ ABBV PFE "
    "CAT GE HON DE COST WMT HD MCD TSLA RIVN SOFI PYPL SNAP DIS").split()))
BENCH = "SPY"
SLIP, RISK, CAP, FLOOR, MAX_POS, MAX_NEW, RR, TSTOP, K = 0.0005, 0.01, 0.15, 0.10, 12, 3, 2.0, 20, 3
VARIANTS = ["S2", "S2_noslow", "S1", "NEAR"]


def atr(b, i, n=14):
    if i < n:
        return None
    return sum(max(b[k]["h"] - b[k]["l"], abs(b[k]["h"] - b[k - 1]["c"]), abs(b[k]["l"] - b[k - 1]["c"]))
               for k in range(i - n + 1, i + 1)) / n


def slope(xs):
    n = len(xs); mx = (n - 1) / 2; my = sum(xs) / n
    return sum((i - mx) * (x - my) for i, x in enumerate(xs)) / sum((i - mx) ** 2 for i in range(n)) / my


def pivots(b):
    """All swing highs/lows as (index, price). Pivot at i is usable from bar i+K."""
    hs, ls = [], []
    for i in range(K, len(b) - K):
        w = b[i - K:i + K + 1]
        if b[i]["h"] == max(x["h"] for x in w):
            hs.append((i, b[i]["h"]))
        if b[i]["l"] == min(x["l"] for x in w):
            ls.append((i, b[i]["l"]))
    return hs, ls


def stage_at(hs, ls, t, lookback=90):
    h = [p for p in hs if t - lookback <= p[0] <= t - K]
    l = [p for p in ls if t - lookback <= p[0] <= t - K]
    def rising(ps, n):
        if len(ps) < n + 1:
            return False
        v = [p[1] for p in ps[-(n + 1):]]
        return all(v[k] < v[k + 1] for k in range(n))
    st = 2 if (rising(h, 2) and rising(l, 2)) else (1 if (rising(h, 1) and rising(l, 1)) else 0)
    return st, (l[-1][1] if l else None)


def signals(b, variant):
    """Return {index: stop} of entry signals at the close of that bar."""
    c = [x["c"] for x in b]
    hs, ls = pivots(b)
    out, prev_ok = {}, False
    for t in range(252, len(b)):
        lo = min(x["l"] for x in b[t - 251:t + 1])
        near = c[t] <= lo * 1.20
        a = atr(b, t)
        if variant == "NEAR":
            ok = near and c[t] > b[t - 1]["h"]
            stop = min(x["l"] for x in b[t - 4:t + 1]) - 0.1 * a if ok else None
        else:
            st, last_low = stage_at(hs, ls, t)
            need = 1 if variant == "S1" else 2
            slowing = slope(c[t - 19:t + 1]) > slope(c[t - 39:t - 19])
            ok = near and st >= need and (slowing or variant == "S2_noslow") and last_low is not None
            stop = last_low - 0.1 * a if ok else None
        if ok and not prev_ok and stop and stop < c[t] and (c[t] - stop) <= 3 * a:
            out[t] = stop
        prev_ok = ok
    return out


def run(data, start, variant):
    idx = {s: {x["d"]: k for k, x in enumerate(bars)} for s, bars in data.items()}
    sig = {s: signals(bars, variant) for s, bars in data.items() if s != BENCH}
    days = sorted(x["d"] for x in data[BENCH] if x["d"] >= start)
    cash, peak, pos, trades, pending, eqh = 100000.0, 100000.0, [], [], [], []

    def equity(d):
        return cash + sum(p["q"] * data[p["s"]][idx[p["s"]][d]]["c"] if d in idx[p["s"]] else p["q"] * p["e"] for p in pos)

    for d in days:
        for o in pending:
            k = idx[o["s"]].get(d)
            if k is None or len(pos) >= MAX_POS or any(p["s"] == o["s"] for p in pos):
                continue
            px = data[o["s"]][k]["o"] * (1 + SLIP)
            if px <= o["stop"]:
                continue
            rps, eq = px - o["stop"], equity(d)
            q = int(min(eq * RISK / rps, eq * CAP / px, max(cash - eq * FLOOR, 0) / px))
            if q <= 0:
                continue
            cash -= q * px
            pos.append({"s": o["s"], "e": px, "stop": o["stop"], "tgt": px + RR * rps, "rps": rps, "q": q, "n": 0, "be": False, "din": d})
        pending = []
        for p in list(pos):
            k = idx[p["s"]].get(d)
            if k is None:
                continue
            bar = data[p["s"]][k]; p["n"] += 1; ex = None
            if bar["o"] <= p["stop"]:
                ex = bar["o"]
            elif bar["l"] <= p["stop"]:
                ex = p["stop"]
            elif bar["o"] >= p["tgt"]:
                ex = bar["o"]
            elif bar["h"] >= p["tgt"]:
                ex = p["tgt"]
            else:
                if not p["be"] and bar["h"] >= p["e"] + p["rps"]:
                    p["be"], p["stop"] = True, p["e"]
                if p["n"] >= TSTOP:
                    ex = bar["c"]
            if ex is not None:
                ex *= (1 - SLIP); cash += p["q"] * ex; pos.remove(p)
                trades.append({"s": p["s"], "in": p["din"], "out": d, "r": (ex - p["e"]) / p["rps"]})
        eq = equity(d); peak = max(peak, eq); eqh.append((d, eq))
        cands = []
        for s, sg in sig.items():
            k = idx[s].get(d)
            if k is not None and k in sg and not any(p["s"] == s for p in pos):
                cands.append({"s": s, "stop": sg[k]})
        pending = cands[:MAX_NEW]
    return trades, eqh


def summarize(trades, eqh, data):
    rs = [t["r"] for t in trades]; n = len(rs)
    out = {"trades": n}
    if n > 1:
        m = sum(rs) / n; sd = math.sqrt(sum((x - m) ** 2 for x in rs) / (n - 1))
        mid = eqh[len(eqh) // 2][0]
        h1 = [t["r"] for t in trades if t["in"] < mid]; h2 = [t["r"] for t in trades if t["in"] >= mid]
        out.update(win_pct=round(100 * sum(x > 0 for x in rs) / n, 1), avg_r=round(m, 3),
                   ci95=[round(m - 1.96 * sd / math.sqrt(n), 3), round(m + 1.96 * sd / math.sqrt(n), 3)],
                   half1_r=round(sum(h1) / len(h1), 3) if h1 else None, half2_r=round(sum(h2) / len(h2), 3) if h2 else None)
    e = [x[1] for x in eqh]; pk, dd = e[0], 0
    for v in e:
        pk = max(pk, v); dd = max(dd, (pk - v) / pk)
    out.update(return_pct=round((e[-1] / 100000 - 1) * 100, 1), max_dd_pct=round(dd * 100, 1))
    spy = [x for x in data[BENCH] if eqh[0][0] <= x["d"] <= eqh[-1][0]]
    out["spy_return_pct"] = round((spy[-1]["c"] / spy[0]["c"] - 1) * 100, 1)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=6)
    ap.add_argument("--csv-dir")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    syms = UNIVERSE + [BENCH]
    end = date.today(); start = end - timedelta(days=int(a.years * 365))
    raw = {}
    if a.csv_dir:
        raw = load_csv_dir(a.csv_dir, syms)
    else:
        for i in range(0, len(syms), 40):
            raw.update(fetch_alpaca(syms[i:i + 40], (start - timedelta(days=400)).isoformat(), end.isoformat()))
    data = {s: sorted(v, key=lambda x: x["d"]) for s, v in raw.items() if len(v) > 300}
    res = {"universe": len(data) - 1, "start": start.isoformat()}
    for v in VARIANTS:
        tr, eqh = run(data, start.isoformat(), v)
        res[v] = summarize(tr, eqh, data)
        print(f"STRUCT {v} {json.dumps(res[v])}")
    near = res["NEAR"].get("avg_r")
    for v in VARIANTS[:-1]:
        r = res[v]
        r["pass"] = bool(r.get("ci95") and r["ci95"][0] > 0 and (r.get("half1_r") or -1) > 0 and (r.get("half2_r") or -1) > 0
                         and r["return_pct"] > 0 and near is not None and r.get("avg_r", -9) > near)
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "structure.json"), "w"), indent=1)
    print("STRUCT_SUMMARY " + json.dumps(res))
