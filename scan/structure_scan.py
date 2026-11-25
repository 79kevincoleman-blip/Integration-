"""Low-vs-own-history + trend-structure scan (risk-sheet.md, owner request 2026-11-25).

For each symbol (2y daily bars from Alpaca market data, keys from GitHub secrets):
  1. How low is it vs its OWN history: % above 1y low, position in 2y range.
  2. Is the fall slowing: 20-day slope vs the prior 20-day slope, range contraction.
  3. Structure: swing pivots (3 bars each side, confirmed only after 3 bars - no look-ahead).
     STAGE 2 = 2 higher lows AND 2 higher highs (owner's rule); STAGE 1 = 1 HL + 1 HH.
  4. History check: every past day the stock was within 15% of its trailing 1y low,
     what happened over the next 20 trading days - for all such days, and for days that
     also had the STAGE 2 structure. Win rate + median, pooled and per symbol.
Writes out/scan.json and prints a compact table. Pure stdlib.
"""
import json, os, sys, urllib.request, urllib.parse, statistics as st
from datetime import date, timedelta

K = 3            # pivot half-width
NEAR_LOW = 0.15  # within 15% of trailing 1y low
FWD = 20         # forward window, trading days


def fetch(symbols, start, end):
    key = os.environ["ALPACA_KEY_ID"].strip()
    sec = os.environ["ALPACA_SECRET_KEY"].strip()
    out = {s: [] for s in symbols}
    token = None
    while True:
        q = {"symbols": ",".join(symbols), "timeframe": "1Day", "start": start, "end": end,
             "limit": 10000, "adjustment": "all", "feed": "iex"}
        if token:
            q["page_token"] = token
        req = urllib.request.Request("https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(q),
                                     headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.loads(r.read())
        for s, bars in (j.get("bars") or {}).items():
            out[s] += [{"d": b["t"][:10], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]} for b in bars]
        token = j.get("next_page_token")
        if not token:
            return out


def pivots(b, upto):
    """Confirmed swing highs/lows using bars[0..upto]."""
    hs, ls = [], []
    for i in range(K, upto - K + 1):
        w = b[i - K:i + K + 1]
        if b[i]["h"] == max(x["h"] for x in w):
            hs.append((i, b[i]["h"]))
        if b[i]["l"] == min(x["l"] for x in w):
            ls.append((i, b[i]["l"]))
    return hs, ls


def stage(b, t, lookback=90):
    hs, ls = pivots(b, t)
    hs = [p for p in hs if p[0] >= t - lookback]
    ls = [p for p in ls if p[0] >= t - lookback]
    def rising(ps, n):
        if len(ps) < n + 1:
            return False
        v = [p[1] for p in ps[-(n + 1):]]
        return all(v[k] < v[k + 1] for k in range(n))
    if rising(hs, 2) and rising(ls, 2):
        return 2
    if rising(hs, 1) and rising(ls, 1):
        return 1
    return 0


def slope(xs):
    n = len(xs)
    mx, my = (n - 1) / 2, sum(xs) / n
    return sum((i - mx) * (x - my) for i, x in enumerate(xs)) / sum((i - mx) ** 2 for i in range(n)) / my


def analyse(b):
    c = [x["c"] for x in b]
    t = len(b) - 1
    lo1, hi1 = min(x["l"] for x in b[-252:]), max(x["h"] for x in b[-252:])
    lo2, hi2 = min(x["l"] for x in b), max(x["h"] for x in b)
    s_now, s_prev = slope(c[-20:]), slope(c[-40:-20])
    rng_now = sum(x["h"] - x["l"] for x in b[-10:]) / 10
    rng_prev = sum(x["h"] - x["l"] for x in b[-30:-10]) / 20
    hs, ls = pivots(b, t)
    # history
    allf, stgf = [], []
    for i in range(252, t - FWD + 1):
        tl = min(x["l"] for x in b[i - 251:i + 1])
        if c[i] <= tl * (1 + NEAR_LOW):
            r = c[i + FWD] / c[i] - 1
            allf.append(r)
            if stage(b, i) == 2:
                stgf.append(r)
    def summ(rs):
        return {"n": len(rs), "win_pct": round(100 * sum(r > 0 for r in rs) / len(rs), 1) if rs else None,
                "median_pct": round(100 * st.median(rs), 2) if rs else None}
    dv = sum(x["c"] * x["v"] for x in b[-20:]) / 20
    return {
        "price": round(c[-1], 2), "pct_above_1y_low": round(100 * (c[-1] / lo1 - 1), 1),
        "pos_in_2y_range_pct": round(100 * (c[-1] - lo2) / (hi2 - lo2), 1),
        "slope20_now_pct_day": round(100 * s_now, 3), "slope20_prev_pct_day": round(100 * s_prev, 3),
        "fall_slowing": s_now > s_prev, "range_contracting": rng_now < rng_prev,
        "stage_now": stage(b, t),
        "last_lows": [round(p[1], 2) for p in ls[-3:]], "last_highs": [round(p[1], 2) for p in hs[-3:]],
        "hist_near_low": summ(allf), "hist_near_low_stage2": summ(stgf),
        "_raw": (allf, stgf), "avg_dollar_vol_m_iex": round(dv / 1e6, 1),
    }


if __name__ == "__main__":
    syms = json.load(open(os.path.join(os.path.dirname(__file__), "universe.json")))["symbols"]
    end = date.today()
    data = {}
    for k in range(0, len(syms), 30):
        data.update(fetch(syms[k:k + 30], (end - timedelta(days=760)).isoformat(), end.isoformat()))
    res, pool_all, pool_stg = {}, [], []
    for s in syms:
        b = sorted(data.get(s, []), key=lambda x: x["d"])
        if len(b) < 300:
            res[s] = {"error": f"only {len(b)} bars"}
            continue
        r = analyse(b)
        a, g = r.pop("_raw")
        pool_all += a; pool_stg += g
        res[s] = r
    def summ(rs):
        return {"n": len(rs), "win_pct": round(100 * sum(x > 0 for x in rs) / len(rs), 1) if rs else None,
                "median_pct": round(100 * st.median(rs), 2) if rs else None}
    out = {"asof": end.isoformat(), "pooled_near_low": summ(pool_all), "pooled_near_low_stage2": summ(pool_stg),
           "symbols": res}
    os.makedirs("out", exist_ok=True)
    json.dump(out, open("out/scan.json", "w"), indent=1)
    print("POOLED near-low:", out["pooled_near_low"], " near-low + stage2:", out["pooled_near_low_stage2"])
    print("sym price above1yLow% pos2y% slowing contracting stage lows highs | hist(all) | hist(stage2)")
    for s, r in sorted(res.items(), key=lambda kv: (-kv[1].get("stage_now", -1), kv[1].get("pct_above_1y_low", 999))):
        if "error" in r:
            print(s, r["error"]); continue
        print(f"ROW {s} {r['price']} {r['pct_above_1y_low']} {r['pos_in_2y_range_pct']} "
              f"{'Y' if r['fall_slowing'] else 'n'} {'Y' if r['range_contracting'] else 'n'} S{r['stage_now']} "
              f"L{r['last_lows']} H{r['last_highs']} | {r['hist_near_low']} | {r['hist_near_low_stage2']} | $vol {r['avg_dollar_vol_m_iex']}M")
