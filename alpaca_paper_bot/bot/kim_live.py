"""Kim-daily live logic (owner 2026-11-25: "Kim replaces current bot"). Same rules as backtest/kim_daily.py (KD_nohist):
signal on COMPLETED daily bars, buy at the next open, initial stop = lowest low since the downtrend event - 0.2 ATR,
then trail: highest close - 2.5 ATR (never lower), breakeven once +1R, momentum-fade exit (after +1R, 2 closes below
EMA10), 30-trading-day max hold. Risk 0.75% per trade, max 8 Kim positions, each <= 12.5% of equity (no leverage).
Stateless: the initial stop is stored in the entry's client_order_id: kd-SYM-YYYYMMDD-s<stop in cents>.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backtest"))
import kim_daily as kd  # noqa: E402

TAG = "kd"
RISK, CAP, MAX_POS, MAX_HOLD = kd.RISK, 0.125, kd.MAX_OPEN, 30


def completed(b, today):
    return [x for x in b if x["d"] != today]


def signal(b):
    """Return the stop if the LAST completed bar is the first reversal trigger after a downtrend event (else None)."""
    if len(b) < 80:
        return None
    k = kd.ind(b)
    n = len(b) - 1
    for e in reversed(kd.events(b, k)):
        i = e["i"]
        if i >= n or i < n - 10:
            continue
        low = b[i]["l"]
        for j in range(i + 1, n + 1):
            low = min(low, b[j]["l"])
            vavg = sum(x["v"] for x in b[j - 20:j]) / 20
            trig = (min(k["rsi"][max(0, j - 19):j + 1]) < 30 and b[j]["c"] > b[j - 1]["h"] and b[j]["c"] > k["e5"][j]
                    and b[j]["v"] >= 1.2 * vavg)
            if trig:
                if j != n:
                    return None  # this event already triggered earlier; the backtest takes only the first trigger
                a = k["atr"][n]
                stop = low - 0.2 * a
                if b[n]["c"] - stop <= 0 or b[n]["c"] - stop > 3 * a:
                    return None
                return round(stop, 2)
        return None
    return None


def trail_state(b, d_in, px, stop0):
    """Replay the backtest's exit rules over completed bars since entry. Returns (stop, exit_reason or None, days)."""
    k = kd.ind(b)
    ent = next((i for i, x in enumerate(b) if x["d"] >= d_in), None)
    if ent is None:
        return stop0, None, 0
    rps = max(px - stop0, 0.01)
    stop, best, below, hit = stop0, px, 0, False
    for j in range(ent, len(b)):
        best = max(best, b[j]["c"])
        hit = hit or b[j]["c"] >= px + rps
        stop = max(stop, best - 2.5 * k["atr"][j], px if hit else stop)
        below = below + 1 if b[j]["c"] < k["e10"][j] else 0
        if hit and below >= 2:
            return stop, "momentum-fade (2 closes below EMA10 after +1R)", len(b) - ent
    days = len(b) - ent
    return stop, ("time stop (30 days)" if days >= MAX_HOLD else None), days


ADOPT_TAGS = ("v42-",)  # owner 2026-11-27: Kim takes over the old bot's positions (GILD, TGT, DLTR); never "manual-"


def entry_info(hist, sym):
    for o in hist or []:  # newest first
        cid = o.get("client_order_id") or ""
        if o["symbol"] != sym or o.get("side") != "buy" or not o.get("filled_at"):
            continue
        if cid.startswith(TAG + "-"):
            try:
                stop0 = int(cid.rsplit("-s", 1)[1]) / 100
            except (IndexError, ValueError):
                return None
            return {"px": float(o["filled_avg_price"]), "d_in": o["filled_at"][:10], "stop0": stop0, "adopted": False}
        if cid.startswith(ADOPT_TAGS):  # adopted: initial stop = that trade's original bracket stop
            stops = [float(l["stop_price"]) for l in o.get("legs") or [] if l.get("stop_price")]
            if not stops:
                return None
            return {"px": float(o["filled_avg_price"]), "d_in": o["filled_at"][:10], "stop0": stops[0], "adopted": True}
    return None


def manage(api, PAPER, data, positions, hist, open_orders, today, dry_run, log):
    """Exits (momentum fade / time) and stop trailing for Kim positions."""
    for p in positions:
        sym = p["symbol"]
        info = entry_info(hist, sym)
        b = completed(data.get(sym) or [], today)
        if not info or not b:
            log["notes"].append(f"{sym}: Kim position but no entry info/bars; left as is")
            continue
        stop, why, days = trail_state(b, info["d_in"], info["px"], info["stop0"])
        mine = [o for o in open_orders or [] if o["symbol"] == sym and o["side"] == "sell"]
        if why:
            act = {"type": "exit", "bot": "kim", "symbol": sym, "qty": p["qty"], "reason": why, "days": days,
                   "unrealized_pl": p.get("unrealized_pl")}
            if not dry_run:
                for o in mine:
                    api(PAPER, "DELETE", f"/v2/orders/{o['id']}")
                act["http"], act["result"] = api(PAPER, "DELETE", f"/v2/positions/{sym}")
            log["actions"].append(act)
            continue
        stop = round(stop, 2)
        if any(o.get("type") == "limit" for o in mine):
            # adopted position still carries the old bot's take-profit/OCO orders: Kim has no profit target,
            # so cancel them and replace with Kim's stop only
            act = {"type": "adopt", "bot": "kim", "symbol": sym, "cancelled": [o["id"] for o in mine]}
            if not dry_run:
                for o in mine:
                    api(PAPER, "DELETE", f"/v2/orders/{o['id']}")
            log["actions"].append(act)
            mine = []
        stops = [o for o in mine if o.get("type") == "stop"]
        if not stops:
            order = {"symbol": sym, "qty": str(abs(int(float(p["qty"])))), "side": "sell", "type": "stop",
                     "stop_price": str(stop), "time_in_force": "gtc"}
            act = {"type": "protect", "bot": "kim", "symbol": sym, "stop": stop}
            if not dry_run:
                act["http"], res = api(PAPER, "POST", "/v2/orders", order)
                if act["http"] != 200:
                    act["result"] = res
            log["actions"].append(act)
        elif float(stops[0]["stop_price"]) < stop - 0.005:  # only ever raise the stop
            act = {"type": "raise-stop", "bot": "kim", "symbol": sym, "from": float(stops[0]["stop_price"]), "to": stop}
            if not dry_run:
                act["http"], res = api(PAPER, "PATCH", f"/v2/orders/{stops[0]['id']}", {"stop_price": str(stop)})
                if act["http"] != 200:
                    act["result"] = res
            log["actions"].append(act)


def entries(api, PAPER, data, universe, held_all, pending, n_kim, equity, cash, today, dry_run, log):
    """Pre-market only: buy at the open (market order) with an attached stop for today (OTO); later runs make it GTC."""
    picks = []
    for sym in sorted(universe):
        if sym in held_all or sym in pending:
            continue
        b = completed(data.get(sym) or [], today)
        stop = signal(b) if b else None
        if stop:
            picks.append((sym, stop, b[-1]["c"]))
    log["kim_signals"] = [s for s, _, _ in picks]
    for sym, stop, ref in picks:
        if n_kim >= MAX_POS:
            log["notes"].append(f"{sym}: Kim signal but 8 Kim positions already open")
            continue
        rps = ref - stop
        qty = int(min(equity * RISK / rps, equity * CAP / ref, max(cash, 0) / ref))
        if qty <= 0:
            log["notes"].append(f"{sym}: Kim signal but no buying power")
            continue
        order = {"symbol": sym, "qty": str(qty), "side": "buy", "type": "market", "time_in_force": "day",
                 "order_class": "oto", "stop_loss": {"stop_price": str(stop)},
                 "client_order_id": f"{TAG}-{sym}-{today.replace('-', '')}-s{int(round(stop * 100))}"}
        act = {"type": "entry", "bot": "kim", "symbol": sym, "qty": qty, "ref_close": ref, "stop": stop,
               "risk_usd_est": round(qty * rps, 2), "notional_usd_est": round(qty * ref, 2)}
        if not dry_run:
            act["http"], res = api(PAPER, "POST", "/v2/orders", order)
            act["order_id"] = res.get("id") if isinstance(res, dict) else res
        log["actions"].append(act)
        cash -= qty * ref
        n_kim += 1
