"""Paper book helpers: sizing, fills, P&L. Pure local math; market data is fed in by hand."""
import json, sys
from pathlib import Path

LEDGER = Path(__file__).with_name("ledger.json")
MAX_POS = 4
MAX_NOTIONAL_PCT = 0.25
DAILY_LOSS_PCT = 0.03
MIN_RR = 2.0


def load():
    return json.loads(LEDGER.read_text())


def save(l):
    LEDGER.write_text(json.dumps(l, indent=2) + "\n")


def equity(l, prices=None):
    prices = prices or {}
    return l["cash"] + sum(p["shares"] * prices.get(p["symbol"], p["entry"]) for p in l["positions"])


def size(entry, stop, target, eq, cash, risk_pct=0.01):
    """Shares for a long trade, or 0 with a reason if a rule blocks it."""
    risk_ps = entry - stop
    if risk_ps <= 0:
        return 0, "stop must be below entry"
    if (target - entry) / risk_ps < MIN_RR:
        return 0, "reward:risk under 2"
    shares = int(eq * risk_pct / risk_ps)
    shares = min(shares, int(eq * MAX_NOTIONAL_PCT / entry), int(cash / entry))
    return (shares, "ok") if shares > 0 else (0, "no buying power")


def can_propose(l, prices=None):
    if len(l["positions"]) >= MAX_POS:
        return False, "max positions"
    if equity(l, prices) <= l["day_start_equity"] * (1 - DAILY_LOSS_PCT):
        return False, "daily loss limit hit"
    return True, "ok"


def step_bar(pos, bar):
    """Apply one 5-min bar {o,h,l,c} to an open long. Returns (exit_price, reason) or None."""
    if bar["o"] <= pos["stop"]:
        return bar["o"], "stop (gap)"
    if bar["l"] <= pos["stop"]:
        return round(pos["stop"] - 0.01, 2), "stop"
    if bar["h"] >= pos["target"]:
        return pos["target"], "target"
    if not pos.get("be") and bar["h"] >= pos["entry"] + (pos["entry"] - pos["stop"]):
        pos["be"] = True
        pos["stop"] = pos["entry"]
    return None


def close(l, pos, price, reason, date):
    pnl = round((price - pos["entry"]) * pos["shares"], 2)
    r = round((price - pos["entry"]) / pos["risk_ps"], 2)
    l["cash"] = round(l["cash"] + price * pos["shares"], 2)
    l["positions"].remove(pos)
    l["closed"].append({**pos, "exit": price, "exit_reason": reason, "pnl": pnl, "r": r, "exit_date": date})
    return pnl, r


if __name__ == "__main__":
    l = load()
    print(f"cash {l['cash']:.2f}  open {len(l['positions'])}  pending {len(l['proposals'])}  closed {len(l['closed'])}")
    if len(sys.argv) == 5:
        e, s, t = map(float, sys.argv[1:4])
        print(size(e, s, t, equity(l), l["cash"], float(sys.argv[4])))
