"""KCkim - owner 2026-11-27: paper-trade Webull-rules version B on Alpaca, SEPARATE from Kim and everything else.

Rules (backtest/webull_rules_backtest.py, variant W_stop_only):
- Entry: Kim-daily buy signal on yesterday's completed bar (bot/kim_live.signal), only if that close <= $15.
  Buy at the open (market order, pre-market run only).
- Size: each position up to 50% of KCkim's own balance; KCkim never spends more than KCkim's own cash. Whole shares.
- Stop (fixed, never moved): by entry price tier: <= $5 -> 50% below entry; $5.01-$10 -> 25%; $10.01-$15 -> 20%.
- Exit: the stop, or after 60 trading days (market sell at the next pre-market run).
KCkim balance: its own $5,000 inside the shared paper account. Balance = $5,000 + realized P&L of its closed trades
+ unrealized P&L of its open ones. Everything it places is tagged: kc- (buys), kcstop- (stops), kcexit- (time exits).
Overlap: Alpaca holds one position per symbol, so KCkim skips any symbol already held or being bought by anyone
(Kim runs first at 08:15; KCkim at 08:25).
"""
import json, os, sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "backtest"))
from live_v41 import api, PAPER, trading_days_between  # noqa: E402
import backtest_v4 as v4  # noqa: E402
import strategy_v42  # noqa: E402
import kim_live as KL  # noqa: E402
from kim_backtest import UNIVERSE as KIM_UNI  # noqa: E402

START, POS_CAP, MAX_PRICE, MAX_HOLD, TAG = 5000.0, 0.50, 15.0, 60, "kc"


def tier_stop(px):
    return round(px * (0.50 if px <= 5 else 0.75 if px <= 10 else 0.80), 2)


def flat(orders):
    for o in orders or []:
        yield o
        for leg in o.get("legs") or []:
            yield leg


def main(dry_run, trial=False):
    log = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "dry_run": dry_run, "actions": [], "notes": []}
    today = date.today().isoformat()
    s, cal = api(PAPER, "GET", f"/v2/calendar?start={(date.today() - timedelta(days=130)).isoformat()}&end={today}")
    if s != 200 or not cal:
        raise SystemExit(f"calendar error {s} {cal}")
    _, clock = api(PAPER, "GET", "/v2/clock")
    if cal[-1]["date"] != today:
        if not (dry_run and trial):
            log["notes"].append("market closed today; nothing to do")
            return log
        last_session = cal[-1]["date"]  # TRIAL: act as the pre-market run of the next session, no orders
        pre_open = True
        log["notes"].append(f"TRIAL (dry run, market closed): using bars through {last_session}; no orders")
    else:
        last_session = cal[-2]["date"]
        pre_open = isinstance(clock, dict) and not clock.get("is_open") and str(clock.get("next_open", ""))[:10] == today
    _, positions = api(PAPER, "GET", "/v2/positions")
    _, open_orders = api(PAPER, "GET", "/v2/orders?status=open&nested=true&limit=200")
    _, hist = api(PAPER, "GET", "/v2/orders?status=closed&limit=500&direction=desc&nested=true")
    hist, open_orders, positions = hist or [], open_orders or [], positions or []

    # --- KCkim's own book from tagged orders ---
    buys = [o for o in hist if (o.get("client_order_id") or "").startswith(TAG + "-") and o.get("side") == "buy"
            and o.get("filled_at")]
    first_buy = {}
    for o in sorted(buys, key=lambda o: o["filled_at"]):
        first_buy.setdefault(o["symbol"], o)
    kc_syms = set(first_buy)
    held = {p["symbol"]: p for p in positions if p["symbol"] in kc_syms}
    realized = 0.0
    for sym, b in first_buy.items():  # closed KCkim trades: buy cost vs every later sell of that symbol
        if sym in held:
            continue
        sells = [x for x in flat(hist) if x.get("symbol") == sym and x.get("side") == "sell" and x.get("filled_at")
                 and x["filled_at"] >= b["filled_at"]]
        realized += sum(float(x["filled_qty"]) * float(x["filled_avg_price"]) for x in sells) \
            - float(b["filled_qty"]) * float(b["filled_avg_price"])
    cost_open = sum(float(p["cost_basis"]) for p in held.values())
    unreal = sum(float(p["unrealized_pl"]) for p in held.values())
    pending = [o for o in open_orders if (o.get("client_order_id") or "").startswith(TAG + "-") and o["side"] == "buy"]
    pending_cost = sum(float(o.get("notional") or 0) or float(o["qty"]) * float(o.get("limit_price") or 0) for o in pending)
    balance = START + realized + unreal
    cash = START + realized - cost_open - pending_cost
    log["kckim"] = {"balance": round(balance, 2), "cash": round(cash, 2), "realized": round(realized, 2),
                    "unrealized": round(unreal, 2), "open": sorted(held), "closed_trades": len(kc_syms) - len(held)}

    # --- manage open KCkim positions: fixed GTC stop at the tier level; 60-day time exit ---
    for sym, p in held.items():
        b = first_buy[sym]
        px = float(b["filled_avg_price"])
        stop = tier_stop(px)
        days = trading_days_between(cal, b["filled_at"][:10], last_session)
        mine = [o for o in open_orders if o["symbol"] == sym and o["side"] == "sell"]
        if days >= MAX_HOLD and pre_open:
            act = {"type": "exit", "bot": "kckim", "symbol": sym, "reason": f"time ({days} trading days)", "qty": p["qty"]}
            if not dry_run:
                for o in mine:
                    api(PAPER, "DELETE", f"/v2/orders/{o['id']}")
                act["http"], res = api(PAPER, "POST", "/v2/orders", {
                    "symbol": sym, "qty": str(abs(int(float(p["qty"])))), "side": "sell", "type": "market",
                    "time_in_force": "day", "client_order_id": f"kcexit-{sym}-{today.replace('-', '')}"})
            log["actions"].append(act)
            continue
        gtc = [o for o in mine if o.get("type") == "stop" and o.get("time_in_force") == "gtc"]
        if gtc:
            continue
        act = {"type": "protect", "bot": "kckim", "symbol": sym, "stop": stop, "replaced": [o["id"] for o in mine]}
        if not dry_run:
            for o in mine:  # the entry's DAY stop leg -> replace with the fixed GTC tier stop
                api(PAPER, "DELETE", f"/v2/orders/{o['id']}")
            act["http"], res = api(PAPER, "POST", "/v2/orders", {
                "symbol": sym, "qty": str(abs(int(float(p["qty"])))), "side": "sell", "type": "stop",
                "stop_price": str(stop), "time_in_force": "gtc",
                "client_order_id": f"kcstop-{sym}-{today.replace('-', '')}"})
            if act["http"] != 200:
                act["result"] = res
        log["actions"].append(act)

    # --- entries: pre-market only ---
    if not pre_open:
        log["notes"].append("KCkim buys only in the pre-market run")
        return log
    universe = sorted(set(strategy_v42.NAMES) | set(KIM_UNI))
    taken = {p["symbol"] for p in positions} | {o["symbol"] for o in open_orders if o["side"] == "buy"}
    start = (date.fromisoformat(last_session) - timedelta(days=420)).isoformat()
    data = v4.fetch_alpaca(universe, start, f"{last_session}T23:00:00Z")
    data = {k: sorted(v, key=lambda x: x["d"]) for k, v in data.items() if v}
    picks = []
    for sym in universe:
        b = [x for x in (data.get(sym) or []) if x["d"] <= last_session]
        if not b or b[-1]["c"] > MAX_PRICE:
            continue
        if KL.signal(b):
            picks.append((sym, b[-1]["c"]))
    log["kckim_signals"] = [s for s, _ in picks]
    for sym, ref in picks:
        if sym in taken:
            log["notes"].append(f"{sym}: KCkim signal but symbol already held/being bought (overlap) - skipped")
            continue
        qty = int(min(balance * POS_CAP, cash) / ref)
        if qty < 1:
            log["notes"].append(f"{sym}: KCkim signal but no KCkim cash left")
            continue
        stop = tier_stop(ref)
        order = {"symbol": sym, "qty": str(qty), "side": "buy", "type": "market", "time_in_force": "day",
                 "order_class": "oto", "stop_loss": {"stop_price": str(stop)},
                 "client_order_id": f"{TAG}-{sym}-{today.replace('-', '')}"}
        act = {"type": "entry", "bot": "kckim", "symbol": sym, "qty": qty, "ref_close": ref, "stop_est": stop,
               "cost_est": round(qty * ref, 2)}
        if not dry_run:
            act["http"], res = api(PAPER, "POST", "/v2/orders", order)
            act["order_id"] = res.get("id") if isinstance(res, dict) else res
        log["actions"].append(act)
        cash -= qty * ref
        taken.add(sym)
    if not log["actions"]:
        log["notes"].append("no KCkim actions")
    return log


if __name__ == "__main__":
    req = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
    print("KCKIM " + json.dumps(main(bool(req.get("dry_run", False)), bool(req.get("trial", False)))))
