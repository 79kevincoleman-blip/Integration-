"""Pre-trade gate for the Webull LIVE account (risk-sheet.md). Returns GO or NO-GO.

Usage: python pretrade.py trade.json   (or import pretrade_check)
trade.json keys: ticker, setup_signal (bool), price, bid, ask, market_cap, entry, stop, target,
                 [new_52w_low_5d, filings_ok - required under $5],
                 order_type (LIMIT), et_time ("HH:MM"), cash, [fees], [unexplained_cash_moves]
"""
import json, sys

TRADING_CAPITAL = 150.0
RISK_PCT = 0.05
MAX_PRICE, PENNY_PRICE = 50.0, 5.0                 # owner 2026-11-25: $50 cap for all Webull tasks
PENNY_MIN_MCAP, PENNY_MAX_SPREAD = 50e6, 0.03       # strategy.md penny limits (under $5)
POS_CAP = 0.25                                       # max 25% of the account per buy
MIN_RR, MAX_BREAKEVEN_WR = 2.0, 0.40
MAX_POSITIONS = 12
PAPER_MIN_TRADES = 30
DEFAULT_FEES = 0.02          # SEC/TAF on a small sell, both sides rounded up


def paper_ok(paper):
    """paper: dict with closed_trades, expectancy_r for this setup."""
    return paper.get("closed_trades", 0) >= PAPER_MIN_TRADES and paper.get("expectancy_r", 0) > 0


def pretrade_check(t, paper=None):
    paper = paper or {"closed_trades": 0, "expectancy_r": 0.0}
    fails, out = [], {"ticker": t["ticker"]}
    entry, stop, target = t.get("entry"), t.get("stop"), t.get("target")

    # 0. written stop + target
    if not stop or not target or not entry:
        fails.append("no written entry/stop/target")
        return _result(out, fails)
    if not stop < entry < target:
        fails.append("need stop < entry < target")
        return _result(out, fails)

    # max positions
    if t.get("open_positions", 0) >= MAX_POSITIONS:
        fails.append(f"already {t['open_positions']} open positions (max {MAX_POSITIONS})")

    # 1. cash discipline
    if t.get("unexplained_cash_moves"):
        fails.append(f"unexplained cash moves {t['unexplained_cash_moves']} - log them in webull-journal.csv")

    # 4. universe: $50 cap; penny limits under $5
    spread = (t["ask"] - t["bid"]) / t["price"]
    out["spread_pct"] = round(spread * 100, 2)
    if t["price"] > MAX_PRICE:
        fails.append(f"price ${t['price']} > ${MAX_PRICE:.0f} cap")
    if t["price"] < PENNY_PRICE:
        if t["market_cap"] < PENNY_MIN_MCAP:
            fails.append(f"penny: market cap ${t['market_cap']/1e6:,.1f}M < $50M")
        if spread > PENNY_MAX_SPREAD:
            fails.append(f"penny: spread {spread*100:.2f}% > 3%")
        if t.get("new_52w_low_5d", True):
            fails.append("penny: new 52-week low in the last 5 days (or not checked)")
        if not t.get("filings_ok", False):
            fails.append("penny: filings not cleared (reverse split / offering / dilution)")

    # 2. size by risk, capped at 25% of the account and the cash on hand
    risk_usd = TRADING_CAPITAL * RISK_PCT
    per_share = entry - stop
    shares = min(risk_usd / per_share, TRADING_CAPITAL * POS_CAP / entry, t["cash"] / entry)
    position = shares * entry
    risk_usd = shares * per_share
    out.update(shares=round(shares, 4), position_usd=round(position, 2), risk_usd=round(risk_usd, 2))

    # 3. costs + breakeven
    fees = t.get("fees", DEFAULT_FEES)
    costs = 2 * spread * position + fees
    reward_usd = shares * (target - entry)
    rr = round((target - entry) / per_share, 4)
    breakeven = (risk_usd + costs) / (reward_usd + risk_usd)
    out.update(rr=round(rr, 2), costs_usd=round(costs, 2), reward_usd=round(reward_usd, 2),
               costs_pct_of_reward=round(100 * costs / reward_usd, 1) if reward_usd else None,
               breakeven_win_rate_no_costs=round(100 / (1 + rr), 1),
               breakeven_win_rate_after_costs=round(100 * breakeven, 1))
    if rr < MIN_RR:
        fails.append(f"reward:risk {rr:.2f} < 2")
    if breakeven > MAX_BREAKEVEN_WR:
        fails.append(f"breakeven win rate after costs {breakeven*100:.1f}% > 40%")

    # 4b. setup signal (webull_strategy.evaluate must say BUY_LOW or BUY_TAKEOFF)
    if not t.get("setup_signal", False):
        fails.append("no reversal/takeoff signal from webull_strategy")

    # 8. order mechanics
    if t.get("order_type", "LIMIT").upper() != "LIMIT":
        fails.append("not a LIMIT order")
    hh, mm = map(int, t.get("et_time", "10:00").split(":"))
    if (hh, mm) < (10, 0):
        fails.append("before 10:00 AM ET")

    # 5. paper first
    if not paper_ok(paper):
        fails.append(f"paper gate: {paper.get('closed_trades', 0)}/{PAPER_MIN_TRADES} closed paper trades, "
                     f"expectancy {paper.get('expectancy_r', 0):+.2f}R")
    return _result(out, fails)


def _result(out, fails):
    out["verdict"] = "GO" if not fails else "NO-GO"
    out["reasons"] = fails
    return out


def show(r):
    print(f"== {r['ticker']}: {r['verdict']}")
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
