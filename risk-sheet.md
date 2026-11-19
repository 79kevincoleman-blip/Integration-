# Risk sheet - Webull LIVE account (the only rulebook for real money)
Replaces webull-strategy.md and weekly-lessons.md. risk-rules.md stays the Alpaca PAPER bot's rules.
Rules only - no account data or credentials.

## 0. THE GATE (hard rule)
No order is placed - by me or by you in the app - until "Run my pre-trade check on TICKER"
returns **GO** (`python pretrade.py`). The check runs BEFORE the order, never after.
No written stop and target = automatic NO-GO.

## 1. Trading money is a fixed amount
- TRADING_CAPITAL = $30 (set in pretrade.py). Decided in advance.
- Nothing tops it up from household money. Every deposit/withdrawal is logged in webull-journal.csv
  the day it happens (type DEPOSIT / WITHDRAWAL, with a reason). Unlogged cash moves = NO-GO
  until explained.

## 2. Size by risk - the ONLY sizing rule
- Risk per trade = 5% of trading capital ($1.50 at $30).
- shares = dollars at risk / (entry - stop). Position cap = whatever that formula gives
  (about $5-7 at $30), never more than the cash on hand. No % position caps, no "50% max".
- Stop goes below the setup's structure (the low that would prove the idea wrong).

## 3. Costs are inside every trade
- Cost per side = spread % x position (conservative: full spread each way) + fees.
- Breakeven win rate = (risk + costs) / (reward + risk). The check prints it for every trade.
- NO-GO if reward:risk < 2:1, or the breakeven win rate after costs is above 40%.

## 4. Universe (liquidity filter, applied before any setup)
- Price > $5, market cap > $1B, bid-ask spread < 0.5% of price.
- This removes dilution / reverse-split names (IMCC, BGSF). No more "near the low of the range"
  screen on illiquid stocks - that shape produced every loss so far.
- Inside the universe the setup is: downtrend, then a confirmed reversal (webull_strategy.py):
  near the downtrend low + at least 1 signal (close above prior high, RSI back above 30, up day
  on 1.5x volume), or a takeoff (higher low + break of the bounce high on volume). No signal = no trade.

## 5. Paper first
- No live setup until the Alpaca paper bot has 30+ CLOSED trades of that setup with positive
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
LIMIT orders only, after 10:00 AM ET, entry at a pullback level. Approval: I send the GO sheet,
you say yes, I create the order, you confirm in the Webull app.
