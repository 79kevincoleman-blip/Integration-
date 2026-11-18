"""Alpaca PAPER bridge, run by GitHub Actions with repo secrets.

Reads alpaca/request.json, calls the Alpaca paper API, prints one JSON result line.
Paper URL is hard-coded; anything else is refused. Keys come only from env vars.
"""
import json, os, sys, urllib.request, urllib.error

PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"


def call(base, method, path, body=None):
    key, sec = os.environ.get("ALPACA_KEY_ID"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not sec:
        raise SystemExit("missing ALPACA_KEY_ID / ALPACA_SECRET_KEY secrets")
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            txt = r.read().decode()
            return r.status, json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


def trim_account(a):
    keep = ["status", "currency", "cash", "equity", "buying_power", "portfolio_value",
            "pattern_day_trader", "trading_blocked", "account_blocked", "shorting_enabled"]
    out = {k: a.get(k) for k in keep} if isinstance(a, dict) else a
    if isinstance(a, dict):
        out["account_number_last4"] = str(a.get("account_number", ""))[-4:]
    return out


def run(req):
    act = req["action"]
    if act == "account":
        s, a = call(PAPER, "GET", "/v2/account")
        return s, trim_account(a)
    if act == "positions":
        return call(PAPER, "GET", "/v2/positions")
    if act == "orders":
        return call(PAPER, "GET", "/v2/orders?status=" + req.get("status", "all") + "&limit=50&nested=true")
    if act == "bracket":  # limit entry + stop + take-profit, all server-side at Alpaca
        o = {"symbol": req["symbol"], "qty": str(req["qty"]), "side": req.get("side", "buy"),
             "type": "limit", "limit_price": str(req["limit"]), "time_in_force": req.get("tif", "gtc"),
             "order_class": "bracket", "client_order_id": req.get("client_id"),
             "take_profit": {"limit_price": str(req["target"])},
             "stop_loss": {"stop_price": str(req["stop"])}}
        return call(PAPER, "POST", "/v2/orders", o)
    if act == "cancel":
        return call(PAPER, "DELETE", "/v2/orders/" + req["order_id"])
    if act == "close":
        return call(PAPER, "DELETE", "/v2/positions/" + req["symbol"])
    if act == "bars":
        return call(DATA, "GET", f"/v2/stocks/{req['symbol']}/bars?timeframe={req.get('tf','1Day')}&limit={req.get('limit',60)}&feed=iex")
    raise SystemExit("unknown action " + act)


if __name__ == "__main__":
    reqs = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "alpaca/request.json"))
    for r in reqs if isinstance(reqs, list) else [reqs]:
        status, result = run(r)
        print("RESULT " + json.dumps({"request": r, "http": status, "result": result}))
