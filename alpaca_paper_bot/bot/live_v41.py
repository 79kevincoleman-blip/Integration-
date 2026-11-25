"""Live v4.2 bot (v4.1 rules + 4 owner changes in backtest/strategy_v42.py: ~330 names, RS top 20,
base <15% & volume 1.3x, 8 positions x 12.5%, 3 per sector, 3 new/day).
Originally: Live v4.1 bot for the Alpaca PAPER account. One run = one trading-day cycle (run before the open).

Rules are the frozen v4.1 rules (backtest/V4_1_PREREGISTRATION.md), implemented with the same code as the backtest:
  scan    63-day relative strength vs SPY > 0, top 10, close > 50d > 200d (stocks + index/sector ETFs)
  entry   high-volume breakout of a 15-30 day base < 12% wide; stop = base midpoint; skip if stop > 2.5 ATR
  orders  bracket: limit buy (yesterday's close + 1% max gap), stop-loss at the stop, take-profit at 3R
  exits   bracket stop / target at Alpaca in real time; structure break (prior close < 50d MA) or 20 trading
          days held -> cancel legs and close at the open
  risk    1% equity per trade, 20% max position, 5 positions, 2 per theme, 10% cash floor, max 2 new per day
  halt    no new entries if equity is 10% below its 1-year peak
LIVE PRICES (owner, 2026-11-19): decisions use real-time IEX last trades. During market hours today's
in-progress bar (open/high/low/volume from 15-min-delayed SIP, volume projected to a full day, last = live
price) is appended before signals and exits are evaluated. Before the open, signals use the prior close,
but entries are skipped if the live pre-market price is >1% above it, and the limit is set from the live price.
This differs from the backtest (decide at close, enter next open).
Stateless: entry dates come from Alpaca order history (client_order_id = v41-SYMBOL-YYYYMMDD).
Paper URL is hard-coded. Keys come only from env vars (GitHub secrets).
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backtest"))
import backtest_v4 as v4  # noqa: E402
import strategy_v42  # noqa: E402,F401  (owner 2026-11-19: all 4 "more trades" changes; patches v4)
import strategy_v43  # noqa: E402  (owner 2026-11-24: switch to C_slots sizing)

PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"
R_MULT, STRUCT_MA, MAX_HOLD, MAX_NEW, MAX_GAP, HALT_DD = 3.0, 50, 20, strategy_v43.MAX_NEW, 0.01, 0.10
LIMIT_SLACK = 0.003  # buy limit = live price + 0.3%
TAG = "v42"


def api(base, method, path, body=None):
    key = os.environ["ALPACA_KEY_ID"].strip()
    sec = os.environ["ALPACA_SECRET_KEY"].strip()
    if not base.startswith("https://paper-api.alpaca.markets") and base != DATA:
        raise SystemExit("refusing non-paper trading URL")
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]


def live_prices(syms):
    """Real-time last trade per symbol from Alpaca's free real-time IEX feed."""
    out = {}
    for i in range(0, len(syms), 50):
        chunk = ",".join(syms[i:i + 50])
        s, j = api(DATA, "GET", f"/v2/stocks/snapshots?symbols={chunk}&feed=iex")
        if s == 200 and isinstance(j, dict):
            for sym, snap in j.items():
                t = (snap or {}).get("latestTrade") or {}
                if t.get("p"):
                    out[sym] = float(t["p"])
    return out


def overlay_today(data, syms, live, today, clock):
    """During market hours, append today's in-progress bar: open/high/low/volume from full-market SIP data
    (15-min delayed on the free plan), last price from real-time IEX. Volume is projected to a full day."""
    end = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat(timespec="seconds").replace("+00:00", "Z")
    q = urllib.parse.urlencode({"symbols": ",".join(syms), "timeframe": "1Day", "start": today, "end": end,
                                "feed": "sip", "adjustment": "all", "limit": 10000})
    s, j = api(DATA, "GET", "/v2/stocks/bars?" + q)
    bars = (j or {}).get("bars", {}) if s == 200 and isinstance(j, dict) else {}
    now = datetime.now(timezone.utc)
    opened = now.replace(hour=14, minute=30, second=0, microsecond=0)  # 9:30 ET in winter (EST)
    if now.month in (4, 5, 6, 7, 8, 9, 10) or (now.month == 3 and now.day > 8) or (now.month == 11 and now.day < 2):
        opened = opened - timedelta(hours=1)  # rough EDT adjustment
    frac = min(max((now - opened).total_seconds() / 23400, 0.1), 1.0)
    for sym in syms:
        b = data.get(sym)
        px = live.get(sym)
        if not b or px is None or b[-1]["d"] == today:
            continue
        tb = (bars.get(sym) or [None])[-1]
        if tb:
            o, h, l, v = tb["o"], max(tb["h"], px), min(tb["l"], px), tb["v"] / frac
        else:
            o, h, l, v = px, px, px, 0
        b.append({"d": today, "o": o, "h": h, "l": l, "c": px, "v": v})


def traded_today(hist, sym, today):
    tag = f"{TAG}-{sym}-{today.replace('-', '')}"
    return any((o.get("client_order_id") or "") == tag for o in hist or [])


def trading_days_between(cal, d0, d1):
    return sum(1 for c in cal if d0 < c["date"] <= d1)


def main(dry_run, trial=False, protect_only=False):
    log = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "dry_run": dry_run, "actions": [], "notes": []}
    today = date.today().isoformat()
    s, cal = api(PAPER, "GET", f"/v2/calendar?start={(date.today() - timedelta(days=60)).isoformat()}&end={today}")
    if s != 200 or not cal:
        raise SystemExit(f"calendar error {s} {cal}")
    if cal[-1]["date"] != today:
        if not (dry_run and trial):
            log["notes"].append("market closed today; nothing to do")
            return log
        # TRIAL (dry run only, market closed): scan as if pre-market of the next session
        last_session = cal[-1]["date"]
        log["notes"].append(f"TRIAL on a closed day: using bars through {last_session}; no orders possible")
    else:
        last_session = cal[-2]["date"]  # bars through yesterday's close

    s, acct = api(PAPER, "GET", "/v2/account")
    _, positions = api(PAPER, "GET", "/v2/positions")
    _, open_orders = api(PAPER, "GET", "/v2/orders?status=open&nested=true&limit=200")
    _, hist = api(PAPER, "GET", "/v2/orders?status=closed&limit=500&direction=desc&nested=true")
    _, ph = api(PAPER, "GET", "/v2/account/portfolio/history?period=1A&timeframe=1D")
    equity, cash = float(acct["equity"]), float(acct["cash"])
    peak = max([x for x in (ph or {}).get("equity", []) if x] + [equity, 100000.0])
    log["account"] = {"equity": equity, "cash": cash, "peak_1y": peak, "positions": len(positions)}

    # the bot only manages positions it opened (client_order_id tag); owner's manual buys are left alone
    bot_syms = {o["symbol"] for o in hist or [] if (o.get("client_order_id") or "").startswith(TAG + "-")
                and o.get("side") == "buy" and o.get("filled_at")}
    held = {p["symbol"]: p for p in positions if p["symbol"] in bot_syms}
    manual = sorted(p["symbol"] for p in positions if p["symbol"] not in bot_syms)
    if manual:
        log["notes"].append("manual positions left alone: " + ", ".join(manual))
    positions = [p for p in positions if p["symbol"] in bot_syms]
    open_orders = [o for o in open_orders or [] if not (o.get("client_order_id") or "").startswith("manual-")]
    syms = sorted(set(v4.NAMES) | {v4.BENCH} | set(held))
    start = (date.fromisoformat(last_session) - timedelta(days=420)).isoformat()
    data = v4.fetch_alpaca(syms, start, f"{last_session}T23:00:00Z")  # explicit UTC end: avoids "recent SIP" 403 in evening runs
    data = {k: sorted(v, key=lambda x: x["d"]) for k, v in data.items() if v}

    # LIVE PRICES (owner 2026-11-19: "get the most up-to-date real time prices before you make a decision")
    live, mode = live_prices(syms), "pre-market"
    _, clock = api(PAPER, "GET", "/v2/clock")
    if isinstance(clock, dict) and clock.get("is_open"):
        mode = "market-open"
        overlay_today(data, syms, live, today, clock)
    log["price_mode"] = mode
    log["live_prices_found"] = sum(1 for s in syms if s in live)

    # entry dates from our filled buy orders
    entry_date = {}
    for o in hist or []:
        cid = o.get("client_order_id") or ""
        if cid.startswith(TAG + "-") and o.get("side") == "buy" and o.get("filled_at"):
            entry_date.setdefault(o["symbol"], o["filled_at"][:10])

    # 1) exits: structure break or time stop -> cancel this symbol's orders and close at the open
    for sym, p in held.items():
        b = data.get(sym)
        if not b:
            log["notes"].append(f"{sym}: no bars, skipped exit check")
            continue
        # owner 2026-11-25: judge the 50d structure exit on COMPLETED daily closes only (as the backtest does),
        # never on today's in-progress bar -- an intraday dip below the 50d must not trigger a sell.
        c = [x["c"] for x in b if x["d"] != today]
        ma = v4.sma(c, STRUCT_MA, len(c) - 1)
        d_in = entry_date.get(sym)
        days_held = trading_days_between(cal, d_in, last_session) if d_in else 0
        why = "structure-break (price < 50d)" if ma and c[-1] < ma else ("time stop (20 days)" if days_held >= MAX_HOLD else None)
        if why:
            act = {"type": "exit", "symbol": sym, "qty": p["qty"], "reason": why, "unrealized_pl": p.get("unrealized_pl")}
            if not dry_run:
                for o in open_orders or []:
                    if o["symbol"] == sym:
                        api(PAPER, "DELETE", f"/v2/orders/{o['id']}")
                act["http"], act["result"] = api(PAPER, "DELETE", f"/v2/positions/{sym}")
            log["actions"].append(act)

    # 1b) protection: every held position must have a live stop + target (bracket legs placed as 'day' expire at
    #     the close; fix 2026-11-24). Re-place them as a GTC OCO using the stop/target from our entry order.
    exiting = {a["symbol"] for a in log["actions"] if a["type"] == "exit"}
    for sym, p in held.items():
        if sym in exiting or any(o["symbol"] == sym and o["side"] == "sell" for o in open_orders or []):
            continue
        stop = tgt = None
        for o in hist or []:  # newest first
            if o["symbol"] == sym and o.get("side") == "buy" and (o.get("client_order_id") or "").startswith(TAG + "-"):
                for leg in o.get("legs") or []:
                    if leg.get("stop_price"):
                        stop = leg["stop_price"]
                    elif leg.get("limit_price"):
                        tgt = leg["limit_price"]
                break
        if not (stop and tgt):
            log["notes"].append(f"{sym}: held but no stop/target found in our orders; NOT protected")
            continue
        oco = {"symbol": sym, "qty": str(abs(int(float(p["qty"])))), "side": "sell", "type": "limit",
               "time_in_force": "gtc", "order_class": "oco",
               "take_profit": {"limit_price": str(tgt)}, "stop_loss": {"stop_price": str(stop)}}
        act = {"type": "protect", "symbol": sym, "qty": oco["qty"], "stop": stop, "target": tgt}
        if not dry_run:
            act["http"], res = api(PAPER, "POST", "/v2/orders", oco)
            if act["http"] != 200:
                act["result"] = res
        log["actions"].append(act)

    # 1c) cancel our unfilled entry orders from earlier days (entries are GTC so their legs survive the close)
    for o in open_orders or []:
        cid = o.get("client_order_id") or ""
        if o["side"] == "buy" and cid.startswith(TAG + "-") and not cid.endswith(today.replace("-", "")):
            if not dry_run:
                api(PAPER, "DELETE", f"/v2/orders/{o['id']}")
            log["actions"].append({"type": "cancel-stale-entry", "symbol": o["symbol"], "order_id": o["id"]})
    open_orders = [o for o in open_orders or [] if not any(a.get("order_id") == o["id"] and a["type"] == "cancel-stale-entry" for a in log["actions"])]

    if protect_only:
        log["notes"].append("protect-only run: no exits/entries evaluated beyond protection")
        return log

    # 2) entries
    if equity < peak * (1 - HALT_DD):
        log["notes"].append(f"HALT: equity {equity:.0f} is >10% below 1y peak {peak:.0f}; no new entries")
        return log
    pending_buys = [o for o in open_orders or [] if o["side"] == "buy"]
    n_pos = len(positions) + len(pending_buys)
    theme_count = {}
    for sym in list(held) + [o["symbol"] for o in pending_buys]:
        t = v4.NAMES.get(sym, "other")
        theme_count[t] = theme_count.get(t, 0) + 1
    spy = data[v4.BENCH]
    spy_ret = spy[-1]["c"] / spy[-1 - v4.RS_LB]["c"] - 1
    rs = []
    for sym, theme in v4.NAMES.items():
        b = data.get(sym)
        if not b or len(b) <= v4.RS_LB or b[-1]["d"] not in (last_session, today):
            continue
        r = b[-1]["c"] / b[-1 - v4.RS_LB]["c"] - 1 - spy_ret
        if r > 0:
            rs.append((r, sym))
    rs.sort(reverse=True)
    log["rs_top"] = [s for _, s in rs[:v4.RS_TOP]]
    new = 0
    for _, sym in rs[:v4.RS_TOP]:
        if new >= MAX_NEW or n_pos >= v4.MAX_POS:
            break
        if sym in held or any(o["symbol"] == sym for o in pending_buys):
            continue
        theme = v4.NAMES[sym]
        if theme_count.get(theme, 0) >= v4.PER_THEME:
            continue
        b = data[sym]
        sig = v4.entry_signal(b, len(b) - 1)
        if not sig or sig[0] != "breakout":
            continue
        if traded_today(hist, sym, today):
            continue
        ref = b[-1]["c"]  # live price when the market is open; prior close before the open
        px = live.get(sym)
        if px is not None and px > ref * (1 + MAX_GAP):
            log["notes"].append(f"{sym}: signal but live price {px:.2f} is >1% above {ref:.2f}; skipped (no chasing)")
            continue
        stop = round(sig[1], 2)
        limit = round((px if px is not None else ref) * (1 + LIMIT_SLACK), 2)
        if limit <= stop:
            continue
        rps = limit - stop
        target = round(limit + R_MULT * rps, 2)
        qty = int(min(equity * v4.RISK / rps, equity * v4.CAP / limit, max(cash - equity * v4.CASH_FLOOR, 0) / limit))
        if qty <= 0:
            log["notes"].append(f"{sym}: signal but no buying power")
            continue
        order = {"symbol": sym, "qty": str(qty), "side": "buy", "type": "limit", "limit_price": str(limit),
                 "time_in_force": "gtc", "order_class": "bracket",
                 "client_order_id": f"{TAG}-{sym}-{today.replace('-', '')}",
                 "take_profit": {"limit_price": str(target)}, "stop_loss": {"stop_price": str(stop)}}
        act = {"type": "entry", "symbol": sym, "theme": theme, "qty": qty, "limit": limit, "stop": stop,
               "target": target, "risk_usd": round(qty * rps, 2), "notional_usd": round(qty * limit, 2)}
        if not dry_run:
            act["http"], res = api(PAPER, "POST", "/v2/orders", order)
            act["order_id"] = res.get("id") if isinstance(res, dict) else res
        log["actions"].append(act)
        cash -= qty * limit
        n_pos += 1
        new += 1
        theme_count[theme] = theme_count.get(theme, 0) + 1
    if not log["actions"]:
        log["notes"].append("no exits, no new breakout signals")
    return log


if __name__ == "__main__":
    req = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
    out = main(bool(req.get("dry_run", False)), bool(req.get("trial", False)), bool(req.get("protect_only", False)))
    print("LIVE_V42 " + json.dumps(out))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("## Alpaca paper bot v4.1\n```json\n" + json.dumps(out, indent=1) + "\n```\n")
