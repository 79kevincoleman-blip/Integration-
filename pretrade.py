"""Pre-trade check for the Webull LIVE account (risk-sheet.md). Writes up a RECOMMENDATION: GO or NO-GO,
with every reason. Owner 2026-11-27: the OWNER has the final say - no order is created until the owner
answers GO, and the owner may say GO to a NO-GO recommendation (logged as an override) or NO to a GO.

Usage: python pretrade.py trade.json   (or import pretrade_check)
trade.json keys: ticker, setup_signal (bool = Kim-daily signal on yesterday's close), price, bid, ask,
                 market_cap, entry (limit price), stop (Kim's initial stop), prior_close,
                 [new_52w_low_5d, filings_ok - required under $5], order_type (LIMIT), et_time ("HH:MM"),
                 cash (available balance), [account_value], [fees], [unexplained_cash_moves], [open_positions]
Owner 2026-11-27: strategy = KIM-DAILY (alpaca_paper_bot/bot/kim_live.py on branch claude/webull-paper-trading-lvj9ad).
Kim has no profit target: it exits on a trailing stop, a momentum fade or 30 trading days, so the old
reward:risk >= 2 and breakeven-win-rate checks are replaced by a cost check (round-trip costs <= 20% of risk).
"""
import json, sys

TRADING_CAPITAL = 150.0
RISK_PCT = 0.01                                      # owner 2026-11-27: 1% of the account per trade
MAX_PRICE, PENNY_PRICE = 20.0, 5.0                 # owner 2026-11-27: stocks priced under $20 only
PENNY_MIN_MCAP, PENNY_MAX_SPREAD = 50e6, 0.03       # strategy.md penny limits (under $5)
POS_CAP = 0.25                                       # max 25% of the account per buy
MAX_COST_OF_RISK = 0.20      # round-trip spread + fees may use at most 20% of the dollars at risk
MAX_GAP_OVER_CLOSE = 0.02     # limit price at most 2% above yesterday's close (Kim buys at the open)
MAX_POSITIONS = 10            # owner 2026-11-27
PAPER_MIN_TRADES = 30
DEFAULT_FEES = 0.02          # SEC/TAF on a small sell, both sides rounded up


def paper_ok(paper):
    """paper: dict with closed_trades, expectancy_r for this setup."""
    return paper.get("closed_trades", 0) >= PAPER_MIN_TRADES and paper.get("expectancy_r", 0) > 0


def pretrade_check(t, paper=None):
    paper = paper or {"closed_trades": 0, "expectancy_r": 0.0}
    fails, out = [], {"ticker": t["ticker"]}
    entry, stop = t.get("entry"), t.get("stop")

    # 0. written entry + stop (Kim's initial stop; it is then trailed up, never down)
    if not stop or not entry:
        fails.append("no written entry/stop")
        return _result(out, fails)
    if not stop < entry:
        fails.append("need stop < entry")
        return _result(out, fails)

    # max positions
    if t.get("open_positions", 0) >= MAX_POSITIONS:
        fails.append(f"already {t['open_positions']} open positions (max {MAX_POSITIONS})")

    # 1. cash discipline
    if t.get("unexplained_cash_moves"):
        fails.append(f"unexplained cash moves {t['unexplained_cash_moves']} - log them in webull-journal.csv")

    # 4. universe: under $20; penny limits under $5
    spread = (t["ask"] - t["bid"]) / t["price"]
    out["spread_pct"] = round(spread * 100, 2)
    if t["price"] >= MAX_PRICE:
        fails.append(f"price ${t['price']} not under ${MAX_PRICE:.0f}")
    if t["price"] < PENNY_PRICE:
        if t["market_cap"] < PENNY_MIN_MCAP:
            fails.append(f"penny: market cap ${t['market_cap']/1e6:,.1f}M < $50M")
        if spread > PENNY_MAX_SPREAD:
            fails.append(f"penny: spread {spread*100:.2f}% > 3%")
        if t.get("new_52w_low_5d", True):
            fails.append("penny: new 52-week low in the last 5 days (or not checked)")
        if not t.get("filings_ok", False):
            fails.append("penny: filings not cleared (reverse split / offering / dilution)")

    # 2. size by 1% risk, capped at 25% of the account and NEVER more than the available balance
    capital = min(t.get("account_value", TRADING_CAPITAL), TRADING_CAPITAL)
    risk_usd = capital * RISK_PCT
    per_share = entry - stop
    shares = min(risk_usd / per_share, capital * POS_CAP / entry, max(t["cash"], 0) / entry)
    if shares <= 0:
        fails.append("no available balance")
        return _result(out, fails)
    position = shares * entry
    risk_usd = shares * per_share
    out.update(shares=round(shares, 4), position_usd=round(position, 2), risk_usd=round(risk_usd, 2))

    # 3. costs must be small next to the risk (Kim has no fixed target)
    fees = t.get("fees", DEFAULT_FEES)
    costs = 2 * spread * position + fees
    out.update(costs_usd=round(costs, 2), costs_pct_of_risk=round(100 * costs / risk_usd, 1) if risk_usd else None)
    if risk_usd and costs > MAX_COST_OF_RISK * risk_usd:
        fails.append(f"costs ${costs:.2f} are {100*costs/risk_usd:.0f}% of the ${risk_usd:.2f} at risk (max 20%)")

    # 4b. setup signal: Kim-daily must flag this stock on yesterday's close
    if not t.get("setup_signal", False):
        fails.append("no Kim-daily signal")

    # 8. order mechanics: LIMIT only, at the open, not chasing a gap
    if t.get("order_type", "LIMIT").upper() != "LIMIT":
        fails.append("not a LIMIT order")
    pc = t.get("prior_close")
    if pc and entry > pc * (1 + MAX_GAP_OVER_CLOSE):
        fails.append(f"limit {entry} is more than 2% above yesterday's close {pc}")
    hh, mm = map(int, t.get("et_time", "09:30").split(":"))
    if (hh, mm) < (9, 30) and not t.get("queued_for_open", True):
        fails.append("before the 9:30 open")

    # 5. paper first
    if not paper_ok(paper):
        fails.append(f"paper gate: {paper.get('closed_trades', 0)}/{PAPER_MIN_TRADES} closed paper trades, "
                     f"expectancy {paper.get('expectancy_r', 0):+.2f}R")
    return _result(out, fails)


def _result(out, fails):
    out["verdict"] = "GO" if not fails else "NO-GO"   # the recommendation
    out["reasons"] = fails
    out["final_say"] = "OWNER"                         # no order until the owner answers GO or NO
    return out


def owner_decision(result, owner_says):
    """Record the owner's final call. Returns the journal note; an order may be created only if 'GO'."""
    d = owner_says.strip().upper()
    if d not in ("GO", "NO"):
        raise ValueError("owner must answer GO or NO")
    note = f"{result['ticker']}: recommended {result['verdict']}, owner said {d}"
    if d == "GO" and result["verdict"] == "NO-GO":
        note += " (OVERRIDE of: " + "; ".join(result["reasons"]) + ")"
    return {"create_order": d == "GO", "note": note}


def show(r):
    print(f"== {r['ticker']}: recommendation {r['verdict']} - final say: owner (answer GO or NO)")
    for k, v in r.items():
        if k not in ("ticker", "verdict", "reasons"):
            print(f"   {k}: {v}")
    for f in r["reasons"]:
        print(f"   x {f}")


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    paper = data.get("paper")
    for t in data["trades"]:
        show(pretrade_check(t, paper))
