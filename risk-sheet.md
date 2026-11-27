# Risk sheet - Webull LIVE account (the only rulebook for real money)
Replaces webull-strategy.md and weekly-lessons.md. risk-rules.md stays the Alpaca PAPER bot's rules.
Rules only - no account data or credentials.

## 0. THE GATE (hard rule)
No order is placed - by me or by you in the app - until "Run my pre-trade check on TICKER"
returns **GO** (`python pretrade.py`). The check runs BEFORE the order, never after.
No written entry and stop = automatic NO-GO.

## 1. Trading money is a fixed amount
- TRADING_CAPITAL = $150 (set in pretrade.py; was $30, owner deposited ~$120 on 2026-11-19). Decided in advance.
- Nothing tops it up from household money. Every deposit/withdrawal is logged in webull-journal.csv
  the day it happens (type DEPOSIT / WITHDRAWAL, with a reason). Unlogged cash moves = NO-GO
  until explained.

## 2. Strategy = KIM-DAILY (owner, 2026-11-27; replaces the reversal/takeoff and structure setups)
Same rules as the Alpaca paper bot (alpaca_paper_bot/bot/kim_live.py, backtest/kim_daily.py on branch
claude/webull-paper-trading-lvj9ad). Decided on yesterday's COMPLETED daily bar, bought at the open.
- Drop: down >= 10% from the 20-day high AND >= 3 x ATR(14); close < 20-day avg < 50-day avg.
- Early warning: RSI(14) < 30 at some point in the last 20 days.
- Buy signal (within 10 days of the drop, first one only): close > prior day's high, close > 5-day EMA,
  volume >= 1.2 x 20-day average.
- Stop: lowest low since the drop - 0.2 ATR (skip if more than 3 ATR away). Then only moves UP:
  highest close - 2.5 ATR; at least breakeven once the trade is up 1R.
- Sell: stop hit; or after +1R, 2 closes in a row below the 10-day EMA; or 30 trading days.
- No profit target.
- Tested: daily, 10 years, ~350 mostly large US stocks: +0.21R/trade, +245% without leverage vs SPY +280%,
  worst drop 21%. NOT tested on stocks under $20 (see 4). Failed on 15-minute bars and on crypto.

## 3. Sizing (owner, 2026-11-27)
- Risk per trade = 1% of trading capital ($1.50 at $150). shares = dollars at risk / (entry - stop).
- Each position at most 25% of the account ($37.50 at $150).
- NEVER more than the available cash balance. No margin.
- Max 10 open positions.
- Fractional shares where Webull allows them.

## 4. Universe (owner, 2026-11-27)
- **Price under $20.00** for every Webull scan, plan, watchlist and buy.
- Under $5, the penny limits also apply: market cap >= $50M, spread <= 3%, no new 52-week low in the
  last 5 trading days, filings checked (reverse splits, offerings, dilution).
- Kim's backtest did not cover a sub-$20 universe; cheap stocks have wider spreads and more failures.
  The paper gate (5) is what proves it.

## 4b. Costs and orders
- Cost per round trip = 2 x spread % x position + fees. NO-GO if costs > 20% of the dollars at risk.
- LIMIT orders only, at most 2% above yesterday's close (Kim buys at the open; no chasing gaps).
- Every Webull order still needs the owner's tap in the app: one alert before 9:30 with the day's Kim buys.

## 5. Paper first
- No live Kim trade until the Alpaca paper bot has 30+ CLOSED Kim trades with positive
  expectancy in R. 30 is a minimum, not proof. Hypothetical/shadow trades do not count.
- R-multiple = profit or loss / dollars risked. Recorded on every trade.

## 6. Scoring (scorecard.py, weekly)
Win rate, average win vs average loss (R), expectancy per trade (R), max drawdown,
and return vs simply holding SPY over the same dates. If SPY wins, the honest answer is:
the long-term SPY sleeve becomes 80% and active trading 20% - not the other way round.

## 7. Loop
- Journal rows come from Webull fills (journal_from_fills.py), not memory.
- One weekly page (weekly.md): scoreboard + the one rule broken that week. No daily reviews.

## 8. Order mechanics (from risk-rules.md 10-11)
LIMIT orders only, placed for the 9:30 open, at most 2% above yesterday's close (Kim, 2026-11-27;
replaces "after 10:00 AM, at a pullback level"). Approval: I send the GO sheet, you say yes, I create
the order, you confirm in the Webull app.
