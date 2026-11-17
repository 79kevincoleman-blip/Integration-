"""Paper swing book helpers: sizing, daily-bar fills, P&L. Pure local math; data is fed in by hand."""
import json, sys
from pathlib import Path

LEDGER = Path(__file__).with_name("ledger.json")
MAX_POS = 5
MAX_NOTIONAL_PCT = 0.20
MAX_LEVERAGED_PCT = 0.10
MIN_CASH_PCT = 0.10
MIN_RR = 2.0
TIME_STOP_DAYS = 10
DD_HALF_RISK = 0.06
DD_STOP = 0.10


def load():
    return json.loads(LEDGER.read_text())


def save(l):
    LEDGER.write_text(json.dumps(l, indent=2) + "\n")


def equity(l, prices=None):
    prices = prices or {}
    return l["cash"] + sum(p["shares"] * prices.get(p["symbol"], p["entry"]) for p in l["positions"])


def risk_pct(eq, high, base=0.01):
    """1% normally, 0.5% once drawdown from equity high reaches 6%."""
    return base / 2 if eq <= high * (1 - DD_HALF_RISK) else base


def size(entry, stop, target, eq, cash, risk=0.01, leveraged=False):
    """Shares for a long trade, or 0 with a reason if a rule blocks it."""
    risk_ps = entry - stop
    if risk_ps <= 0:
        return 0, "stop must be below entry"
    if (target - entry) / risk_ps < MIN_RR:
        return 0, "reward:risk under 2"
    cap = MAX_LEVERAGED_PCT if leveraged else MAX_NOTIONAL_PCT
    spendable = cash - eq * MIN_CASH_PCT
    shares = min(int(eq * risk / risk_ps), int(eq * cap / entry), int(max(spendable, 0) / entry))
    return (shares, "ok") if shares > 0 else (0, "no buying power")


def can_propose(l, theme, prices=None):
    eq = equity(l, prices)
    if eq <= l["equity_high"] * (1 - DD_STOP):
        return False, "drawdown stop: review required"
    if len(l["positions"]) >= MAX_POS:
        return False, "max positions"
    if any(p.get("theme") == theme for p in l["positions"]):
        return False, f"already hold a {theme} position"
    return True, "ok"


def step_day(pos, bar):
    """Apply one daily bar {o,h,l,c} to an open long. Returns (exit_price, reason) or None."""
    pos["days"] = pos.get("days", 0) + 1
    if bar["o"] <= pos["stop"]:
        return bar["o"], "stop (gap)"
    if bar["l"] <= pos["stop"]:
        return round(pos["stop"] - 0.01, 2), "stop"
    if bar["o"] >= pos["target"]:
        return bar["o"], "target (gap)"
    if bar["h"] >= pos["target"]:
        return pos["target"], "target"
    if not pos.get("be") and bar["h"] >= pos["entry"] + (pos["entry"] - pos["stop"]):
        pos["be"] = True
        pos["stop"] = pos["entry"]
    if pos["days"] >= TIME_STOP_DAYS:
        return bar["c"], "time stop"
    return None


def close(l, pos, price, reason, date):
    pnl = round((price - pos["entry"]) * pos["shares"], 2)
    r = round((price - pos["entry"]) / pos["risk_ps"], 2)
    l["cash"] = round(l["cash"] + price * pos["shares"], 2)
    l["positions"].remove(pos)
    l["closed"].append({**pos, "exit": price, "exit_reason": reason, "pnl": pnl, "r": r, "exit_date": date})
    return pnl, r


def scorecard(l):
    rs = [t["r"] for t in l["closed"]]
    if not rs:
        return {"trades": 0}
    wins = sum(x for x in rs if x > 0)
    losses = -sum(x for x in rs if x < 0)
    return {"trades": len(rs), "win_rate": round(sum(x > 0 for x in rs) / len(rs), 2),
            "expectancy_r": round(sum(rs) / len(rs), 2),
            "profit_factor": round(wins / losses, 2) if losses else None}


if __name__ == "__main__":
    l = load()
    print(f"cash {l['cash']:.2f}  open {len(l['positions'])}  pending {len(l['proposals'])}  {scorecard(l)}")
    if len(sys.argv) == 4:
        e, s, t = map(float, sys.argv[1:4])
        eq = equity(l)
        print(size(e, s, t, eq, l["cash"], risk_pct(eq, l["equity_high"])))
