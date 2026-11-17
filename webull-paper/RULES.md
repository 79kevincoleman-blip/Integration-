# Paper Swing-Trading Book ($100,000 virtual) — v2 (from 2026-11-17)

v1 (intraday day trading) retired: owner can't approve trades within minutes during work hours,
so 3 proposals in 4 days all expired. v2 holds positions 2-10 days so one approval per day is enough.

## Approval flow
- One pre-market alert (~8:20 ET) with up to 2 proposals. Each is good for the whole trading day.
- Owner replies **Y** / **N** (or `Y 1`, `N 2`) any time before 3:30 ET. No reply = expires at 3:30.
- On Y the order is a limit buy, filled only if price trades inside the entry zone that day.
- The protective stop and target are part of the approved trade: exits happen without asking.

## Risk (hard limits)
1. Risk per trade = 1% of equity: shares = equity*1% / (entry - stop).
2. Max position notional 20% of equity. Max 5 open positions. At least 10% cash.
3. Max 1 open position per theme (e.g. semis, AI infra, energy, banks, biotech, index-inverse).
4. Inverse ETFs (SQQQ, SOXS, SPXS, SH, PSQ) allowed as "long" positions to profit from falling markets.
   Leveraged ETFs: max 10% notional, max 5-day hold.
5. Book drawdown -6% from equity high: risk drops to 0.5% until a new high. -10%: stop and review.
6. Earnings within the planned hold window: no new entry (exception: inverse/index ETFs).
7. Minimum reward:risk 2:1 to target.
8. Fresh sector-negative headline (<15 min before entry) voids a long setup in that sector.

## Exits
- Stop: below the setup's structure (prior swing low / breakout base), typically 1-2x daily ATR.
- Target: 2R. At +1R move stop to breakeven.
- Time stop: exit at the close after 10 trading days if neither stop nor target hit.
- Daily bars decide fills: stop first if a day's range hits both stop and target (conservative).

## Setups (daily charts)
- **Pullback in uptrend**: price > 50-day MA, 50 > 200, pulls back 3-8% to the 20-day MA or prior breakout, then a green day closes above the prior day's high. Stop under the pullback low.
- **Base breakout**: 3-6 week tight range (<12% wide), close above the range high on >1.5x avg volume. Stop under the range midpoint.
- **Downtrend short via inverse ETF**: index/sector below 50-day MA, failed bounce at the 20-day MA. Buy the inverse ETF, stop above the bounce high (in index terms).

## Scorecard (pass/fail after 30 closed trades)
- Pass: expectancy > +0.2R per trade, max drawdown < 8%, profit factor > 1.3.
- Pass = start proposing real-account versions (owner confirms each in Webull).
- Fail = review the rules before continuing.

## Schedule (ET, weekdays)
- 08:17 pre-market scan + proposals (push alert)
- 12:47 midday: fill approved orders, manage stops
- 15:47 close: fill/manage, expire unanswered proposals, daily recap (push)
