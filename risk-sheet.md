# Risk sheet - Webull LIVE account (the only rulebook for real money)
Replaces webull-strategy.md and weekly-lessons.md. risk-rules.md stays the Alpaca PAPER bot's rules.
Rules only - no account data or credentials.

## 0. THE CHECK, THEN THE OWNER DECIDES (owner, 2026-11-27)
Before any order, "Run my pre-trade check on TICKER" (`python pretrade.py`) writes up a
**recommendation: GO or NO-GO**, with every reason. No written entry and stop = recommendation NO-GO.
**The owner has the final say.** No order is created until the owner answers GO or NO.
The owner may say GO to a NO-GO recommendation - that is logged in webull-journal.csv as an OVERRIDE
with the reasons it overrode - or NO to a GO. Every other rule below feeds the recommendation.

## 1. Trading money = the real Webull balance (owner, 2026-11-28)
- Capital = the actual Webull account balance at the time of the check ("150 keep or whatever is my balance").
  $150 is used only if no balance is given. Nothing tops it up from household money.
- Every deposit/withdrawal is logged in webull-journal.csv the day it happens (type DEPOSIT / WITHDRAWAL,
  with a reason). Unlogged cash moves = NO-GO until explained.

## 2. Strategy = VERSION B (owner "Yes", 2026-11-28) - same as the Alpaca paper bot KCkim
(alpaca_paper_bot/bot/kckim_live.py on branch claude/webull-paper-trading-lvj9ad)
- ENTRY = Kim-daily buy signal on yesterday's COMPLETED daily bar, bought at the open:
  - Drop: down >= 10% from the 20-day high AND >= 3 x ATR(14); close < 20-day avg < 50-day avg.
  - RSI(14) < 30 at some point in the last 20 days.
  - Signal (within 10 days of the drop, first one only): close > prior day's high, close > 5-day EMA,
    volume >= 1.2 x 20-day average.
- STOP = fixed, by entry price, NEVER moved:
  - $5.00 and under: 50% below entry (buy at $4.00 -> stop $2.00)
  - $5.01 - $10.00: 25% below entry
  - $10.01 - $15.00: 20% below entry
- EXIT = the stop, or after 60 trading days. No trailing stop, no profit target.
- Backtest (10y, $5k start): +1,496% but a 79% worst drop (-55% in 2026 alone), $10-15 tier lost money,
  heavy survivorship bias. Kim's trailing exits on top of these stops LOST (-24.5%). Unproven - see 5.

## 3. Sizing (owner, 2026-11-27/28)
- Each position up to 50% of the balance.
- All positions together NEVER more than the balance: only the cash still available can be spent
  (18 sh at $4 = $72 of $150 -> about $78 left for the next buy). No margin.
- Max 10 open positions.
- Fractional shares where Webull allows them.

## 4. Universe (owner, 2026-11-28)
- **Price at or under $15.00** for every Webull scan, plan, watchlist and buy.
- Under $5, the penny limits also apply: market cap >= $50M, spread <= 3%, no new 52-week low in the
  last 5 trading days, filings checked (reverse splits, offerings, dilution).

## 4b. Costs and orders
- Cost per round trip = 2 x spread % x position + fees. NO-GO if costs > 20% of the dollars at risk.
- LIMIT orders only, at most 2% above yesterday's close (Kim buys at the open; no chasing gaps).
- Every Webull order still needs the owner's tap in the app: one alert before 9:30 with the day's Kim buys.

## 5. Paper first
- Recommendation is NO-GO until the Alpaca paper bot KCkim has 30+ CLOSED version-B trades with positive
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
replaces "after 10:00 AM, at a pullback level"). Webull: place the tier stop as a GTC stop right after the fill. Approval: I send the GO sheet, you say yes, I create
the order, you confirm in the Webull app.
