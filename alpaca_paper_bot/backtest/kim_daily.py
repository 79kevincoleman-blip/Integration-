"""KIM-DAILY — Kim's reversal idea on DAILY bars, 10 years. ONE SHOT, PRE-REGISTERED 2026-11-25 before the run.

Why: intraday Kim failed twice (2y, 15-min). Owner agreed to one final test on daily charts with frozen rules.
No re-tuning after this run, whatever the result.

Universe: the live bot's ~308 large caps + ETFs (strategy_v42) + Kim's volatile names. Daily SIP bars, split-adjusted.
 1 DOWNTREND EVENT  drop from the 20-day high to today's low >= 10% AND >= 3 x ATR(14); close < SMA20 < SMA50.
                    One event per stock per 10 days.
 2 STOCK HISTORY    past events of the same stock whose outcome is already known (no look-ahead). "Reversed" = within
                    20 days price regained half the drop before falling 1 ATR below the event low.
                    Need >= 5 past events and reversal rate >= MIN_RATE (variant).
 3 EARLY WARNING    RSI(14) < 30 at some point in the 20 days up to the trigger.
 4 TRIGGER          within 10 days of the event: close > prior day's high, close > EMA5, volume >= 1.2 x 20-day avg.
                    Buy next day's open.
 5 STOP             lowest low since the event - 0.2 ATR; skip if > 3 ATR away.
 6 SELL             trailing stop = highest close - 2.5 ATR (never below initial stop); breakeven once +1R;
                    after +1R, 2 closes below EMA10 -> sell at that close; max hold 30 trading days.
 Risk 0.75% per trade, max 8 open. Slippage 10 bps per side. Stop is checked first when a bar hits stop and target.
Variants: KD_nohist, KD_hist35 (owner's 35%), KD_hist50.
PASS: avg R 95% CI low > 0, avg R > 0 in both halves, return > 0, and (history variants) avg R > KD_nohist.
"""
import argparse, json, math, os, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(__file__))
from backtest import fetch_alpaca  # noqa: E402
import strategy_v42  # noqa: E402
from kim_backtest import UNIVERSE as KIM_UNI, ema  # noqa: E402

SLIP, RISK, MAX_OPEN = 0.0010, 0.0075, 8
VARIANTS = {"KD_nohist": None, "KD_hist35": 0.35, "KD_hist50": 0.50}


def ind(b):
    c = [x["c"] for x in b]
    tr = [b[0]["h"] - b[0]["l"]] + [max(b[i]["h"], c[i - 1]) - min(b[i]["l"], c[i - 1]) for i in range(1, len(b))]
    atr, a = [], None
    for x in tr:
        a = x if a is None else (a * 13 + x) / 14
        atr.append(a)
    rsi, ag, al = [], None, None
    for i in range(len(c)):
        g = max(c[i] - c[i - 1], 0) if i else 0
        l = max(c[i - 1] - c[i], 0) if i else 0
        ag = g if ag is None else (ag * 13 + g) / 14
        al = l if al is None else (al * 13 + l) / 14
        rsi.append(100 - 100 / (1 + ag / al) if al else 100)
    sma = lambda n: [sum(c[i - n + 1:i + 1]) / n if i >= n - 1 else None for i in range(len(c))]
    return {"c": c, "atr": atr, "rsi": rsi, "s20": sma(20), "s50": sma(50), "e5": ema(c, 5), "e10": ema(c, 10)}


def events(b, k):
    ev, last = [], -99
    for i in range(60, len(b)):
        if i - last < 10:
            continue
        hi, lo, a = max(x["h"] for x in b[i - 19:i + 1]), b[i]["l"], k["atr"][i]
        drop = hi - lo
        if not (a and drop >= 0.10 * hi and drop >= 3 * a and k["s50"][i] and k["c"][i] < k["s20"][i] < k["s50"][i]):
            continue
        last = i
        goal, fail, rev, known = lo + 0.5 * drop, lo - a, False, min(i + 20, len(b) - 1)
        for j in range(i + 1, min(i + 21, len(b))):
            if b[j]["l"] <= fail:
                known = j
                break
            if b[j]["h"] >= goal:
                rev, known = True, j
                break
        ev.append({"i": i, "rev": rev, "known": known})
    return ev


def trades(sym, b, k, ev, min_rate):
    out = []
    for n, e in enumerate(ev):
        i = e["i"]
        past = [p for p in ev[:n] if p["known"] < i]
        rate = sum(p["rev"] for p in past) / len(past) if past else 0
        if min_rate is not None and (len(past) < 5 or rate < min_rate):
            continue
        low, ent = b[i]["l"], None
        for j in range(i + 1, min(i + 11, len(b) - 1)):
            low = min(low, b[j]["l"])
            vavg = sum(x["v"] for x in b[j - 20:j]) / 20
            if (min(k["rsi"][max(0, j - 19):j + 1]) < 30 and b[j]["c"] > b[j - 1]["h"] and b[j]["c"] > k["e5"][j]
                    and b[j]["v"] >= 1.2 * vavg):
                ent = j + 1
                break
        if ent is None:
            continue
        a = k["atr"][ent - 1]
        px, stop0 = b[ent]["o"] * (1 + SLIP), low - 0.2 * a
        rps = px - stop0
        if rps <= 0 or rps > 3 * a:
            continue
        stop, best, below, hit, ex, why, j = stop0, px, 0, False, None, None, ent
        for j in range(ent, min(ent + 30, len(b))):
            bar = b[j]
            if bar["o"] <= stop:
                ex, why = bar["o"], "stop-gap"
                break
            if bar["l"] <= stop:
                ex, why = stop, "stop" if stop < px else "trail"
                break
            best = max(best, bar["c"])
            hit = hit or bar["c"] >= px + rps
            stop = max(stop, best - 2.5 * k["atr"][j], px if hit else stop)
            below = below + 1 if bar["c"] < k["e10"][j] else 0
            if hit and below >= 2:
                ex, why = bar["c"], "momentum-fade"
                break
        if ex is None:
            ex, why = b[j]["c"], "time"
        ex *= 1 - SLIP
        out.append({"sym": sym, "in": b[ent]["d"], "out": b[j]["d"], "r": round((ex - px) / rps, 3), "why": why,
                    "hist_n": len(past), "hist_rate": round(rate, 2), "peak_r": round((best - px) / rps, 2),
                    "rps_pct": round(rps / px, 4)})
    return out


def simulate(tr, cap=None):
    """cap: max position size as a fraction of equity (realism check: no leverage)."""
    tr = sorted(tr, key=lambda t: t["in"])
    eq, opn, taken, curve = 100000.0, [], [], []
    for t in tr:
        opn = [o for o in opn if o["out"] >= t["in"]]
        if len(opn) >= MAX_OPEN:
            continue
        opn.append(t)
        risk = RISK if cap is None else min(RISK, cap * t["rps_pct"])
        eq += eq * risk * t["r"]
        taken.append(t)
        curve.append((t["out"], eq))
    return taken, curve


def stats(tr, curve, t0, t1):
    tr = [t for t in tr if t0 <= t["in"] <= t1]
    out = {"trades": len(tr)}
    if len(tr) < 2:
        return out
    rs = [t["r"] for t in tr]
    n, m = len(rs), sum(rs) / len(rs)
    sd = math.sqrt(sum((x - m) ** 2 for x in rs) / (n - 1))
    w, l = sum(x for x in rs if x > 0), -sum(x for x in rs if x < 0)
    prev = [v for d, v in curve if d < t0]
    start = prev[-1] if prev else 100000.0
    eq = [v for d, v in curve if t0 <= d <= t1]
    peak, mdd = start, 0
    for v in eq:
        peak, mdd = max(peak, v), max(mdd, (peak - v) / peak)
    out.update({"win_rate": round(sum(x > 0 for x in rs) / n, 3), "avg_r": round(m, 3),
                "avg_r_95ci": [round(m - 1.96 * sd / math.sqrt(n), 3), round(m + 1.96 * sd / math.sqrt(n), 3)],
                "profit_factor": round(w / l, 2) if l else None,
                "return_pct": round(((eq[-1] if eq else start) / start - 1) * 100, 1), "max_dd_pct": round(mdd * 100, 1),
                "avg_peak_r": round(sum(t["peak_r"] for t in tr) / n, 2),
                "by_exit": {k: sum(t["why"] == k for t in tr) for k in sorted({t["why"] for t in tr})}})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--years", default="10"); ap.add_argument("--out", default="out")
    a = ap.parse_args()
    yrs = float(str(a.years).split(",")[-1])
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=int(yrs * 365) + 120)
    syms = sorted(set(strategy_v42.NAMES) | set(KIM_UNI))
    data = fetch_alpaca(syms, start.isoformat(), f"{end.isoformat()}T23:00:00Z")
    data = {s: sorted(v, key=lambda x: x["d"]) for s, v in data.items() if len(v) > 120}
    t0 = (end - timedelta(days=int(yrs * 365))).isoformat()
    spy = [x for x in data["SPY"] if x["d"] >= t0]
    days = [x["d"] for x in spy]
    mid = days[len(days) // 2]
    P = {"full": (days[0], days[-1]), "first_half": (days[0], mid), "second_half": (mid, days[-1])}
    pre = {s: (b, ind(b)) for s, b in data.items()}
    evs = {s: events(b, k) for s, (b, k) in pre.items()}
    allev = [e for v in evs.values() for e in v if pre and True]
    res = {"periods": {k: f"{v[0]} to {v[1]}" for k, v in P.items()}, "symbols_loaded": len(data),
           "events_total": len(allev), "event_reversal_rate_all": round(sum(e["rev"] for e in allev) / max(1, len(allev)), 3),
           "SPY": {k: round((next(x["c"] for x in reversed(spy) if x["d"] <= v[1]) /
                             next(x["c"] for x in spy if x["d"] >= v[0]) - 1) * 100, 1) for k, v in P.items()}}
    all_tr = {}
    for name, rate in VARIANTS.items():
        cand = [t for s, (b, k) in pre.items() for t in trades(s, b, k, evs[s], rate) if t["in"] >= t0]
        taken, curve = simulate(cand)
        all_tr[name] = taken
        res[name] = {k: stats(taken, curve, *v) for k, v in P.items()}
        res[name]["candidates"] = len(cand)
    # realism check added after run 1 (2026-11-25; NOT a rule change): same KD_nohist trades, each position capped
    # at 12.5% of equity (no leverage), plus per-year results.
    cand = [t for s, (b, k) in pre.items() for t in trades(s, b, k, evs[s], None) if t["in"] >= t0]
    taken, curve = simulate(cand, cap=0.125)
    res["KD_nohist_cap12.5"] = {k: stats(taken, curve, *v) for k, v in P.items()}
    yrs_ = sorted({t["in"][:4] for t in all_tr["KD_nohist"]})
    res["KD_nohist_by_year"] = {y: {"trades": sum(t["in"][:4] == y for t in all_tr["KD_nohist"]),
                                    "avg_r": round(sum(t["r"] for t in all_tr["KD_nohist"] if t["in"][:4] == y) /
                                                   max(1, sum(t["in"][:4] == y for t in all_tr["KD_nohist"])), 3)} for y in yrs_}
    res["avg_position_pct_uncapped"] = round(sum(RISK / t["rps_pct"] for t in all_tr["KD_nohist"]) / max(1, len(all_tr["KD_nohist"])) * 100, 1)
    base = res["KD_nohist"]["full"].get("avg_r", -9)
    ver = {}
    for name in VARIANTS:
        f, h1, h2 = res[name]["full"], res[name]["first_half"], res[name]["second_half"]
        c = {"ci_low_pos": f.get("avg_r_95ci", [-1])[0] > 0,
             "both_halves_pos": h1.get("avg_r", -1) > 0 and h2.get("avg_r", -1) > 0, "return_pos": f.get("return_pct", -1) > 0}
        if name != "KD_nohist":
            c["history_helps"] = f.get("avg_r", -9) > base
        c["PASS"] = all(c.values())
        ver[name] = c
    res["verdict"] = ver
    os.makedirs(a.out, exist_ok=True)
    json.dump({"summary": res, "trades": all_tr}, open(os.path.join(a.out, "kim_daily.json"), "w"), indent=1)
    print("SUMMARY_KIMD " + json.dumps(res))
