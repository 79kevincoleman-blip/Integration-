# Risk sheet - Webull LIVE account (the only rulebook for real money)
Replaces webull-strategy.md and weekly-lessons.md. risk-rules.md stays the Alpaca PAPER bot's rules.
Rules only - no account data or credentials.

## 0. THE GATE (hard rule)
No order is placed - by me or by you in the app - until "Run my pre-trade check on TICKER"
returns **GO** (`python pretrade.py`). The check runs BEFORE the order, never after.
No written stop and target = automatic NO-GO.

## 1. Trading money is a fixed amount
- TRADING_CAPITAL = $150 (set in pretrade.py; was $30, owner deposited ~$120 on 2026-11-19). Decided in advance.
- Nothing tops it up from household money. Every deposit/withdrawal is logged in webull-journal.csv
  the day it happens (type DEPOSIT / WITHDRAWAL, with a reason). Unlogged cash moves = NO-GO
  until explained.

## 2. Sizing (owner, 2026-11-25 - same rules as slickRick / strategy.md, ALL Webull tasks)
- Risk per trade = 5% of trading capital ($7.50 at $150). shares = dollars at risk / (entry - stop).
- Max buy size = 25% of the account per position (caps the share count). Never more than cash on hand.
- Max 12 open positions, each sized by the risk rule (most end up well under 25%).
- Stop goes below the setup's structure (the low that would prove the idea wrong).

## 3. Costs are inside every trade
- Cost per side = spread % x position (conservative: full spread each way) + fees.
- Breakeven win rate = (risk + costs) / (reward + risk). The check prints it for every trade.
- NO-GO if reward:risk < 2:1, or the breakeven win rate after costs is above 40%.

## 4. Universe (applied before any setup) - owner, 2026-11-25
- **Price $50.00 or under** for every Webull scan, plan, watchlist and buy.
- Under $5, all strategy.md penny limits also apply: market cap >= $50M, spread <= 3%,
  no new 52-week low in the last 5 trading days, filings checked (reverse splits, offerings, dilution).
  These block IMCC-type names (IMCC ~$2M cap, TNMG ~$1.7M, USDE no revenue).
- (Replaces the earlier $5 minimum / $1B cap / 0.5% spread filter.)
- Inside the universe the setup is: downtrend, then a confirmed reversal (webull_strategy.py):
  near the downtrend low + at least 1 signal (close above prior high, RSI back above 30, up day
  on 1.5x volume), or a takeoff (higher low + break of the bounce high on volume). No signal = no trade.
- **Backtest 2026-11-19 (paper bot, 3y, liquid names): FAILED** - 233 trades, 36% win, -0.05R per trade,
  -8.6% vs SPY +65.5%. This setup cannot go live. A new setup must pass the paper bot's backtest first.

## 4c. Structure check (owner, 2026-11-25) - scan/structure_scan.py
- Look for any stock trading low versus ITS OWN history (near its 1y low / bottom of its 2y range),
  not only reversals.
- Then require the fall to slow (20-day slope flattening, smaller daily ranges) and a structure of
  2 higher lows AND 2 higher highs (stage 2). 1 HL + 1 HH = stage 1 = watch only.
- Compare with that stock's history: past times it was this close to its low, how often was it up 20
  trading days later, with and without the stage-2 structure.
- Reputation check before any GO: analyst ratings, recent news, dilution/reverse splits, debt.

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
