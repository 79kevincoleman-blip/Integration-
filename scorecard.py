"""Scorecard from webull-journal.csv (risk-sheet.md section 6). Writes weekly.md with --weekly."""
import csv, sys


def load(path="webull-journal.csv"):
    return list(csv.DictReader(open(path)))


def score(rows, start_equity, spy_return_pct=None):
    closed = [r for r in rows if r["type"] == "TRADE" and r["side"] == "SELL" and r["r_multiple"]]
    rs = [float(r["r_multiple"]) for r in closed]
    wins, losses = [x for x in rs if x > 0], [x for x in rs if x <= 0]
    eq, peak, dd = start_equity, start_equity, 0.0
    for r in rows:
        if r["type"] == "TRADE" and r["side"] == "SELL" and r["pnl_usd"]:
            eq += float(r["pnl_usd"])
            peak = max(peak, eq)
            dd = max(dd, (peak - eq) / peak)
    s = {
        "closed_trades": len(rs),
        "win_rate_pct": round(100 * len(wins) / len(rs), 1) if rs else None,
        "avg_win_r": round(sum(wins) / len(wins), 2) if wins else None,
        "avg_loss_r": round(sum(losses) / len(losses), 2) if losses else None,
        "expectancy_r": round(sum(rs) / len(rs), 2) if rs else None,
        "max_drawdown_pct": round(100 * dd, 1),
        "return_pct": round(100 * (eq - start_equity) / start_equity, 1),
        "spy_return_pct": spy_return_pct,
        "cash_moves": [(r["date"], r["type"], r["pnl_usd"], r["note"]) for r in rows
                       if r["type"] in ("DEPOSIT", "WITHDRAWAL", "UNEXPLAINED")],
    }
    if spy_return_pct is not None:
        s["beats_spy"] = s["return_pct"] > spy_return_pct
    return s


def weekly(s, rule_broken, path="weekly.md"):
    lines = ["# Weekly scoreboard", ""]
    lines += [f"- {k}: {v}" for k, v in s.items() if k != "cash_moves"]
    lines += ["", "## Cash moves (must all be explained)"]
    lines += [f"- {d} {t} {a} {n}" for d, t, a, n in s["cash_moves"]] or ["- none"]
    lines += ["", f"## The one rule broken this week", f"- {rule_broken}", ""]
    open(path, "w").write("\n".join(lines))


if __name__ == "__main__":
    s = score(load(), float(sys.argv[1]) if len(sys.argv) > 1 else 30.0,
              float(sys.argv[2]) if len(sys.argv) > 2 else None)
    for k, v in s.items():
        print(f"{k}: {v}")
