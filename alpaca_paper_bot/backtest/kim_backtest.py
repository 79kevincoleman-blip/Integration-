"""KIM — intraday downtrend-reversal bot (owner spec 2026-11-24). PRE-REGISTERED before the first run.

Owner: "recognize patterns in graphical data, understand a downward trend, know if it's a common thing for that
stock and how often it has reversed, recognize it before and at the time of reversal, flag it for a grab, then hold
it until the up trend slows and stops and sell at or near the height." Owner choices: 15-min bars, auto-buy on
paper, volatile small caps included.

Rules (15-minute bars, regular hours only, all times US/Eastern):
 1 DOWNTREND EVENT  drop from the 52-bar (2-day) high to the current low >= 5 x ATR(14), and close < EMA20 < EMA50.
                    One event per stock per 26 bars (cooldown).
 2 STOCK HISTORY    for that stock, past events whose outcome is already known (no look-ahead). An event "reversed"
                    if, within the next 52 bars, price regained half the drop before falling 1 ATR below the event low.
                    Need >= 5 past events and a reversal rate >= MIN_RATE (variant).
 3 EARLY WARNING    RSI(14) dipped below 30 during the drop (selling exhaustion). Required.
 4 REVERSAL TRIGGER within 26 bars of the event: a bar closes above the prior bar's high and above EMA9, on volume
                    >= 1.3 x its 20-bar average. Buy at the next bar's open. No entries after 15:15.
 5 STOP             lowest low since the event - 0.2 ATR. Skip if the stop is > 3 ATR away.
 6 SELL ("near the high")  trailing stop = highest close since entry - 2.5 ATR (never below the initial stop);
                    once up 1R the stop moves to at least breakeven; momentum fade = after +1R, two closes in a row
                    below EMA9 -> sell at that close. Flat at the 15:45 bar close (no overnight).
 Risk: 0.5% of equity per trade, max 3 open, max 6 entries/day. Costs: 10 bps slippage per side.

Variants: K_nohist (skip rule 2), K_hist50 (rate >= 0.50), K_hist60 (rate >= 0.60).
Run 1 (2026-11-25): FAIL; hist50/hist60 took 0 trades (base reversal rate 31%). Run 2: owner asked for a 35%
bounce record -> K_hist35, plus K_hist40 as a robustness check. POST-HOC: a pass needs out-of-sample paper proof.
PASS (decided before the run) for a variant: avg R 95% CI lower bound > 0, avg R > 0 in both halves, total return
> 0 after costs, AND the history filter must beat K_nohist on avg R (otherwise rule 2 adds nothing).
"""
import argparse, json, math, os, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DATA = "https://data.alpaca.markets"
UNIVERSE = ("MARA RIOT CLSK HUT WULF CIFR BITF MSTR COIN HOOD SOFI AFRM UPST PLTR TSLA NVDA AMD SMCI MU INTC "
            "RIVN LCID NIO F GM AAL CCL NCLH RCL UBER DKNG ROKU SNAP PINS RBLX U PATH AI SOUN BBAI IONQ RGTI QBTS "
            "RKLB ASTS ACHR JOBY OKLO SMR HIMS CELH ENPH FSLR PLUG GME AMC CVNA OPEN SHOP NET CRWD APP TNMG SKYD "
            "SPY QQQ IWM").split()
SLIP, RISK, MAX_OPEN, MAX_DAY = 0.0010, 0.005, 3, 6
VARIANTS = {"K_nohist": None, "K_hist35": 0.35, "K_hist40": 0.40}  # 2026-11-25 owner: 35% bounce record (post-hoc; 40% added as a robustness check)


def fetch(syms, start, end, tf="15Min"):
    key, sec = os.environ["ALPACA_KEY_ID"].strip(), os.environ["ALPACA_SECRET_KEY"].strip()
    out = {s: [] for s in syms}
    for i in range(0, len(syms), 20):
        chunk, token = syms[i:i + 20], None
        while True:
            q = {"symbols": ",".join(chunk), "timeframe": tf, "start": start, "end": end, "limit": 10000,
                 "adjustment": "all", "feed": "sip"}
            if token:
                q["page_token"] = token
            req = urllib.request.Request(f"{DATA}/v2/stocks/bars?" + urllib.parse.urlencode(q),
                                         headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(req, timeout=60) as r:
                        js = json.loads(r.read().decode())
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        time.sleep(5 * (attempt + 1))
                        continue
                    raise SystemExit(f"bars error {e.code} {e.read().decode()[:300]}")
            for s, bars in (js.get("bars") or {}).items():
                for b in bars:
                    t = datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET)
                    hm = t.hour * 60 + t.minute
                    if 570 <= hm <= 945:  # 09:30 .. 15:45 bar starts
                        out[s].append({"t": t, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]})
            token = js.get("next_page_token")
            if not token:
                break
    return {s: v for s, v in out.items() if len(v) > 300}


def ema(xs, n):
    k, out, e = 2 / (n + 1), [], None
    for x in xs:
        e = x if e is None else e + k * (x - e)
        out.append(e)
    return out


def indicators(b):
    c = [x["c"] for x in b]
    tr = [b[0]["h"] - b[0]["l"]] + [max(b[i]["h"], c[i - 1]) - min(b[i]["l"], c[i - 1]) for i in range(1, len(b))]
    atr, a = [], None
    for x in tr:
        a = x if a is None else (a * 13 + x) / 14
        atr.append(a)
    gains = [0] + [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    losses = [0] + [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    rsi, ag, al = [], None, None
    for g, l in zip(gains, losses):
        ag = g if ag is None else (ag * 13 + g) / 14
        al = l if al is None else (al * 13 + l) / 14
        rsi.append(100 - 100 / (1 + ag / al) if al else 100)
    return {"c": c, "atr": atr, "rsi": rsi, "e9": ema(c, 9), "e20": ema(c, 20), "e50": ema(c, 50)}


def events_for(b, ind):
    """Downtrend events with their (future) outcome and the bar index at which the outcome became known."""
    ev, last = [], -999
    for i in range(60, len(b)):
        if i - last < 26:
            continue
        hi = max(x["h"] for x in b[i - 52:i + 1])
        lo = b[i]["l"]
        a = ind["atr"][i]
        if a <= 0 or (hi - lo) < 5 * a or not (ind["c"][i] < ind["e20"][i] < ind["e50"][i]):
            continue
        last = i
        drop = hi - lo
        goal, fail, rev, known = lo + 0.5 * drop, lo - a, False, None
        low_run = lo
        for j in range(i + 1, min(i + 53, len(b))):
            low_run = min(low_run, b[j]["l"])
            if b[j]["l"] <= fail:
                known = j
                break
            if b[j]["h"] >= goal:
                rev, known = True, j
                break
        if known is None:
            known = min(i + 52, len(b) - 1)
        ev.append({"i": i, "hi": hi, "lo": lo, "rev": rev, "known": known})
    return ev


def trades_for(sym, b, ind, ev, min_rate):
    out = []
    for k, e in enumerate(ev):
        i = e["i"]
        past = [p for p in ev[:k] if p["known"] < i]
        rate = sum(p["rev"] for p in past) / len(past) if past else 0
        if min_rate is not None and (len(past) < 5 or rate < min_rate):
            continue
        low, rsi_low, entry_i = b[i]["l"], min(ind["rsi"][max(0, i - 52):i + 1]), None
        for j in range(i + 1, min(i + 27, len(b) - 1)):
            low = min(low, b[j]["l"])
            rsi_low = min(rsi_low, ind["rsi"][j])
            vavg = sum(x["v"] for x in b[j - 20:j]) / 20
            if (rsi_low < 30 and b[j]["c"] > b[j - 1]["h"] and b[j]["c"] > ind["e9"][j] and b[j]["v"] >= 1.3 * vavg
                    and b[j]["t"].date() == b[j + 1]["t"].date()
                    and b[j + 1]["t"].hour * 60 + b[j + 1]["t"].minute <= 915):
                entry_i = j + 1
                break
        if entry_i is None:
            continue
        a = ind["atr"][entry_i - 1]
        px = b[entry_i]["o"] * (1 + SLIP)
        stop0 = low - 0.2 * a
        rps = px - stop0
        if rps <= 0 or rps > 3 * a:
            continue
        stop, best, below, hit1r, ex, why = stop0, px, 0, False, None, None
        for j in range(entry_i, len(b)):
            bar = b[j]
            if j > entry_i and bar["t"].date() != b[j - 1]["t"].date():
                ex, why = b[j - 1]["c"], "eod"
                break
            if bar["o"] <= stop:
                ex, why = bar["o"], "stop-gap"
                break
            if bar["l"] <= stop:
                ex, why = stop, "stop" if stop < px else "trail"
                break
            best = max(best, bar["c"])
            if bar["c"] >= px + rps:
                hit1r = True
            stop = max(stop, best - 2.5 * ind["atr"][j], px if hit1r else stop)
            below = below + 1 if bar["c"] < ind["e9"][j] else 0
            if hit1r and below >= 2:
                ex, why = bar["c"], "momentum-fade"
                break
            if bar["t"].hour * 60 + bar["t"].minute >= 945:
                ex, why = bar["c"], "eod"
                break
        if ex is None:
            continue
        ex *= 1 - SLIP
        out.append({"sym": sym, "t_in": b[entry_i]["t"].isoformat(), "t_out": b[min(j, len(b) - 1)]["t"].isoformat(),
                    "r": round((ex - px) / rps, 3), "why": why, "hist_n": len(past), "hist_rate": round(rate, 2),
                    "peak_r": round((best - px) / rps, 2)})
    return out


def simulate(trades):
    trades = sorted(trades, key=lambda t: t["t_in"])
    eq, open_, taken, per_day, curve = 100000.0, [], [], {}, []
    for t in trades:
        open_ = [o for o in open_ if o["t_out"] > t["t_in"]]
        d = t["t_in"][:10]
        if len(open_) >= MAX_OPEN or per_day.get(d, 0) >= MAX_DAY:
            continue
        per_day[d] = per_day.get(d, 0) + 1
        open_.append(t)
        eq += eq * RISK * t["r"]
        taken.append(t)
        curve.append((t["t_out"], eq))
    return taken, curve


def stats(tr, curve, t0, t1):
    tr = [t for t in tr if t0 <= t["t_in"][:10] <= t1]
    out = {"trades": len(tr)}
    if len(tr) < 2:
        return out
    rs = [t["r"] for t in tr]
    n, m = len(rs), sum(rs) / len(rs)
    sd = math.sqrt(sum((x - m) ** 2 for x in rs) / (n - 1))
    w, l = sum(x for x in rs if x > 0), -sum(x for x in rs if x < 0)
    eq = [v for d, v in curve if t0 <= d[:10] <= t1]
    peak, mdd, start = 100000.0, 0, None
    prev = [v for d, v in curve if d[:10] < t0]
    start = prev[-1] if prev else 100000.0
    peak = start
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
    ap = argparse.ArgumentParser(); ap.add_argument("--years", default="2"); ap.add_argument("--out", default="out")
    a = ap.parse_args()
    yrs = float(str(a.years).split(",")[-1])
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=int(yrs * 365))
    data = fetch(UNIVERSE, f"{start.isoformat()}T00:00:00Z", f"{end.isoformat()}T23:00:00Z")
    print(f"loaded {len(data)} symbols, {sum(len(v) for v in data.values())} bars", flush=True)
    warm = (start + timedelta(days=120)).isoformat()  # first 4 months only build stock history
    days = sorted({x["t"].date().isoformat() for v in data.values() for x in v if x["t"].date().isoformat() >= warm})
    mid = days[len(days) // 2]
    P = {"full": (days[0], days[-1]), "first_half": (days[0], mid), "second_half": (mid, days[-1])}
    prepped = {}
    for s, b in data.items():
        ind = indicators(b)
        prepped[s] = (b, ind, events_for(b, ind))
    res = {"periods": {k: f"{v[0]} to {v[1]}" for k, v in P.items()}, "symbols_loaded": sorted(data),
           "events_total": sum(len(p[2]) for p in prepped.values()),
           "event_reversal_rate_all": round(sum(e["rev"] for p in prepped.values() for e in p[2]) /
                                            max(1, sum(len(p[2]) for p in prepped.values())), 3)}
    all_tr = {}
    for name, rate in VARIANTS.items():
        cand = [t for s, (b, ind, ev) in prepped.items() for t in trades_for(s, b, ind, ev, rate) if t["t_in"][:10] >= warm]
        taken, curve = simulate(cand)
        all_tr[name] = taken
        res[name] = {k: stats(taken, curve, *v) for k, v in P.items()}
        res[name]["candidates"] = len(cand)
    base = res["K_nohist"]["full"].get("avg_r", -9)
    verdict = {}
    for name in VARIANTS:
        f, h1, h2 = res[name]["full"], res[name]["first_half"], res[name]["second_half"]
        c = {"ci_low_pos": f.get("avg_r_95ci", [-1])[0] > 0, "both_halves_pos": h1.get("avg_r", -1) > 0 and h2.get("avg_r", -1) > 0,
             "return_pos": f.get("return_pct", -1) > 0}
        if name != "K_nohist":
            c["history_helps"] = f.get("avg_r", -9) > base
        c["PASS"] = all(c.values())
        verdict[name] = c
    res["verdict"] = verdict
    os.makedirs(a.out, exist_ok=True)
    json.dump({"summary": res, "trades": all_tr}, open(os.path.join(a.out, "kim.json"), "w"), indent=1, default=str)
    print("SUMMARY_KIM " + json.dumps(res, default=str))
