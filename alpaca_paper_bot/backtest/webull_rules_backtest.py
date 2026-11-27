"""WEBULL RULES test (owner 2026-11-27, "Run it let's see how it holds up"). Rules decided BEFORE this run:
- Entry: Kim-daily buy signal (kim_daily.py), buy at next open. Only stocks priced <= $15 at the signal close.
- Size: each position up to 50% of the balance (equity), total invested never more than cash on hand. Whole shares.
- Initial stop by price tier at entry: <= $5 -> 50% below entry; $5.01-$10 -> 25%; $10.01-$15 -> 20%.
- Variant A "W_kim_exits": that stop, then Kim's exits (trail = best close - 2.5 ATR never lower, breakeven after +1R,
  momentum fade after +1R, 30-day max).
- Variant B "W_stop_only": that stop only; otherwise hold up to 60 trading days.
- Start $150. Costs 20 bps per side (cheap stocks). Stop checked first when a bar hits stop and other exits.
Not modelled: penny checks (market cap, spread, filings) - no historical data for them; owner GO/NO.
Universe: same ~348 names as Kim-daily (survivorship bias: today's names). Reported vs SPY buy-and-hold.
"""
import argparse, json, math, os, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(__file__))
from backtest import fetch_alpaca  # noqa: E402
import strategy_v42  # noqa: E402
import kim_daily as kd  # noqa: E402
from kim_backtest import UNIVERSE as KIM_UNI  # noqa: E402

SLIP, START, MAX_PRICE, POS_CAP = 0.0020, 150.0, 15.0, 0.50


def tier_stop(px):
    return px * (0.50 if px <= 5 else 0.75 if px <= 10 else 0.80)


def trades(sym, b, k, ev, mode):
    out = []
    for e in ev:
        i, ent = e["i"], None
        for j in range(i + 1, min(i + 11, len(b) - 1)):
            vavg = sum(x["v"] for x in b[j - 20:j]) / 20
            if (min(k["rsi"][max(0, j - 19):j + 1]) < 30 and b[j]["c"] > b[j - 1]["h"] and b[j]["c"] > k["e5"][j]
                    and b[j]["v"] >= 1.2 * vavg):
                ent = j + 1
                break
        if ent is None or b[ent - 1]["c"] > MAX_PRICE:
            continue
        px = b[ent]["o"] * (1 + SLIP)
        stop0 = tier_stop(px)
        rps = px - stop0
        stop, best, below, hit, ex, why = stop0, px, 0, False, None, None
        hold = 30 if mode == "kim" else 60
        for j in range(ent, min(ent + hold, len(b))):
            bar = b[j]
            if bar["o"] <= stop:
                ex, why = bar["o"], "stop-gap"
                break
            if bar["l"] <= stop:
                ex, why = stop, "stop" if stop < px else "trail"
                break
            if mode == "kim":
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
        out.append({"sym": sym, "in": b[ent]["d"], "out": b[j]["d"], "px": px, "ex": ex, "stop_pct": round(1 - stop0 / px, 2),
                    "ret": round(ex / px - 1, 4), "why": why})
    return out


def simulate(cands):
    """Cash account: buy up to 50% of equity (never more than cash); whole shares; positions close at their exit."""
    cands = sorted(cands, key=lambda t: (t["in"], t["sym"]))
    cash, opn, taken, curve = START, [], [], []
    for t in cands:
        for o in sorted([o for o in opn if o["out"] < t["in"]], key=lambda o: o["out"]):
            cash += o["sh"] * o["ex"]
            opn.remove(o)
            curve.append((o["out"], cash + sum(p["sh"] * p["px"] for p in opn)))
        if any(o["sym"] == t["sym"] for o in opn):
            continue
        equity = cash + sum(p["sh"] * p["px"] for p in opn)  # open positions at cost (approximation)
        sh = int(min(equity * POS_CAP, cash) / t["px"])
        if sh < 1:
            continue
        cash -= sh * t["px"]
        o = dict(t, sh=sh, pnl=round(sh * (t["ex"] - t["px"]), 2), pct_of_equity=round(sh * t["px"] / equity, 3))
        opn.append(o)
        taken.append(o)
    for o in sorted(opn, key=lambda o: o["out"]):
        cash += o["sh"] * o["ex"]
        curve.append((o["out"], cash))
    return taken, curve


def stats(taken, curve, t0, t1):
    tr = [t for t in taken if t0 <= t["in"] <= t1]
    out = {"trades": len(tr)}
    if len(tr) < 2:
        return out
    rets = [t["ret"] for t in tr]
    prev = [v for d, v in curve if d < t0]
    start = prev[-1] if prev else START
    eq = [v for d, v in curve if t0 <= d <= t1]
    peak, mdd, streak, worst = start, 0, 0, 0
    for v in eq:
        peak, mdd = max(peak, v), max(mdd, (peak - v) / peak)
    for t in sorted(tr, key=lambda t: t["out"]):
        streak = streak + 1 if t["pnl"] < 0 else 0
        worst = max(worst, streak)
    n, m = len(rets), sum(rets) / len(rets)
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / (n - 1))
    out.update({"win_rate": round(sum(r > 0 for r in rets) / n, 3), "avg_trade_pct": round(m * 100, 2),
                "avg_trade_95ci_pct": [round((m - 1.96 * sd / math.sqrt(n)) * 100, 2), round((m + 1.96 * sd / math.sqrt(n)) * 100, 2)],
                "start_usd": round(start, 2), "end_usd": round(eq[-1] if eq else start, 2),
                "return_pct": round(((eq[-1] if eq else start) / start - 1) * 100, 1), "max_dd_pct": round(mdd * 100, 1),
                "worst_losing_streak": worst, "biggest_loss_usd": round(min(t["pnl"] for t in tr), 2),
                "biggest_win_usd": round(max(t["pnl"] for t in tr), 2),
                "by_exit": {k: sum(t["why"] == k for t in tr) for k in sorted({t["why"] for t in tr})},
                "by_tier": {lab: {"trades": len(g), "avg_pct": round(sum(t["ret"] for t in g) / len(g) * 100, 2) if g else None}
                            for lab, g in (("<=5 (50% stop)", [t for t in tr if t["stop_pct"] >= 0.49]),
                                           ("5-10 (25% stop)", [t for t in tr if 0.24 <= t["stop_pct"] < 0.26]),
                                           ("10-15 (20% stop)", [t for t in tr if 0.19 <= t["stop_pct"] < 0.21]))}})
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
    pre = {s: (b, kd.ind(b)) for s, b in data.items()}
    evs = {s: kd.events(b, k) for s, (b, k) in pre.items()}
    res = {"periods": {k: f"{v[0]} to {v[1]}" for k, v in P.items()}, "symbols_loaded": len(data),
           "SPY_pct": {k: round((next(x["c"] for x in reversed(spy) if x["d"] <= v[1]) /
                                 next(x["c"] for x in spy if x["d"] >= v[0]) - 1) * 100, 1) for k, v in P.items()}}
    for name, mode in (("W_kim_exits", "kim"), ("W_stop_only", "stop")):
        cand = [t for s, (b, k) in pre.items() for t in trades(s, b, k, evs[s], mode) if t["in"] >= t0]
        taken, curve = simulate(cand)
        res[name] = {k: stats(taken, curve, *v) for k, v in P.items()}
        res[name]["signals_under_15"] = len(cand)
        res[name]["by_year_usd_end"] = {}
        for y in sorted({d[:4] for d, _ in curve}):
            res[name]["by_year_usd_end"][y] = round([v for d, v in curve if d[:4] == y][-1], 2)
    os.makedirs(a.out, exist_ok=True)
    json.dump({"summary": res}, open(os.path.join(a.out, "webull_rules.json"), "w"), indent=1)
    print("SUMMARY_WEBULL " + json.dumps(res))
