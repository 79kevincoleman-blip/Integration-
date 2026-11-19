"""Live v4.1 bot for the Alpaca PAPER account. One run = one trading-day cycle (run before the open).

Rules are the frozen v4.1 rules (backtest/V4_1_PREREGISTRATION.md), implemented with the same code as the backtest:
  scan    63-day relative strength vs SPY > 0, top 10, close > 50d > 200d (stocks + index/sector ETFs)
  entry   high-volume breakout of a 15-30 day base < 12% wide; stop = base midpoint; skip if stop > 2.5 ATR
  orders  bracket: limit buy (yesterday's close + 1% max gap), stop-loss at the stop, take-profit at 3R
  exits   bracket stop / target at Alpaca in real time; structure break (prior close < 50d MA) or 20 trading
          days held -> cancel legs and close at the open
  risk    1% equity per trade, 20% max position, 5 positions, 2 per theme, 10% cash floor, max 2 new per day
  halt    no new entries if equity is 10% below its 1-year peak
Stateless: entry dates come from Alpaca order history (client_order_id = v41-SYMBOL-YYYYMMDD).
Paper URL is hard-coded. Keys come only from env vars (GitHub secrets).
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backtest"))
import backtest_v4 as v4  # noqa: E402

PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"
R_MULT, STRUCT_MA, MAX_HOLD, MAX_NEW, MAX_GAP, HALT_DD = 3.0, 50, 20, 2, 0.01, 0.10
TAG = "v41"


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


def trading_days_between(cal, d0, d1):
    return sum(1 for c in cal if d0 < c["date"] <= d1)


def main(dry_run):
    log = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "dry_run": dry_run, "actions": [], "notes": []}
    today = date.today().isoformat()
    s, cal = api(PAPER, "GET", f"/v2/calendar?start={(date.today() - timedelta(days=60)).isoformat()}&end={today}")
    if s != 200 or not cal:
        raise SystemExit(f"calendar error {s} {cal}")
    if cal[-1]["date"] != today:
        log["notes"].append("market closed today; nothing to do")
        return log
    last_session = cal[-2]["date"]  # bars through yesterday's close

    s, acct = api(PAPER, "GET", "/v2/account")
    _, positions = api(PAPER, "GET", "/v2/positions")
    _, open_orders = api(PAPER, "GET", "/v2/orders?status=open&nested=true&limit=200")
    _, hist = api(PAPER, "GET", "/v2/orders?status=closed&limit=500&direction=desc&nested=true")
    _, ph = api(PAPER, "GET", "/v2/account/portfolio/history?period=1A&timeframe=1D")
    equity, cash = float(acct["equity"]), float(acct["cash"])
    peak = max([x for x in (ph or {}).get("equity", []) if x] + [equity, 100000.0])
    log["account"] = {"equity": equity, "cash": cash, "peak_1y": peak, "positions": len(positions)}

    held = {p["symbol"]: p for p in positions}
    syms = sorted(set(v4.NAMES) | {v4.BENCH} | set(held))
    start = (date.fromisoformat(last_session) - timedelta(days=420)).isoformat()
    data = v4.fetch_alpaca(syms, start, last_session)
    data = {k: sorted(v, key=lambda x: x["d"]) for k, v in data.items() if v}

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
        c = [x["c"] for x in b]
        ma = v4.sma(c, STRUCT_MA, len(c) - 1)
        d_in = entry_date.get(sym)
        days_held = trading_days_between(cal, d_in, last_session) if d_in else 0
        why = "structure-break (close < 50d)" if ma and c[-1] < ma else ("time stop (20 days)" if days_held >= MAX_HOLD else None)
        if why:
            act = {"type": "exit", "symbol": sym, "qty": p["qty"], "reason": why, "unrealized_pl": p.get("unrealized_pl")}
            if not dry_run:
                for o in open_orders or []:
                    if o["symbol"] == sym:
                        api(PAPER, "DELETE", f"/v2/orders/{o['id']}")
                act["http"], act["result"] = api(PAPER, "DELETE", f"/v2/positions/{sym}")
            log["actions"].append(act)

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
        if not b or len(b) <= v4.RS_LB or b[-1]["d"] != last_session:
            continue
        r = b[-1]["c"] / b[-1 - v4.RS_LB]["c"] - 1 - spy_ret
        if r > 0:
            rs.append((r, sym))
    rs.sort(reverse=True)
    log["rs_top10"] = [s for _, s in rs[:v4.RS_TOP]]
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
        ref = b[-1]["c"]
        stop = round(sig[1], 2)
        limit = round(ref * (1 + MAX_GAP), 2)
        rps = limit - stop
        target = round(limit + R_MULT * rps, 2)
        qty = int(min(equity * v4.RISK / rps, equity * v4.CAP / limit, max(cash - equity * v4.CASH_FLOOR, 0) / limit))
        if qty <= 0:
            log["notes"].append(f"{sym}: signal but no buying power")
            continue
        order = {"symbol": sym, "qty": str(qty), "side": "buy", "type": "limit", "limit_price": str(limit),
                 "time_in_force": "day", "order_class": "bracket",
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
    out = main(bool(req.get("dry_run", False)))
    print("LIVE_V41 " + json.dumps(out))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("## Alpaca paper bot v4.1\n```json\n" + json.dumps(out, indent=1) + "\n```\n")
