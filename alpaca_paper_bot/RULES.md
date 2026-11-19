# ACTIVE STRATEGY: v4.1 LIVE on Alpaca paper (from 2026-11-19, owner: "Let alpaca be fully automated")
Frozen rules: backtest/V4_1_PREREGISTRATION.md. Code: bot/live_v41.py. Workflow: .github/workflows/alpaca-live.yml.
- Fully automatic, no approvals. One run per trading day before the open.
- Scan: 63-day relative strength vs SPY > 0, top 10, close > 50d > 200d (stocks + index/sector ETFs).
- Entry: high-volume breakout of a 15-30 day base < 12% wide only. Bracket order: limit = prior close + 1%,
  stop = base midpoint (skip if > 2.5 ATR), take-profit = 3R. Day order; unfilled cancels at the close.
- Exit: stop/target held at Alpaca (real time); prior close < 50d MA or 20 trading days held -> close at the open.
- Risk: 1% equity/trade, 20% max position, 5 positions, 2 per theme, 10% cash floor, max 2 new per day.
- Halt: no new entries while equity is > 10% below its 1-year peak.
- Purpose: out-of-sample evidence for v4.1 (backtest passed 3/4 checks; too few trades to prove the edge).
- Everything below this section is history (v2 and earlier), kept for reference.

---

# Paper Swing-Trading Book ($100,000 virtual) — v2 (from 2026-11-17)

v1 (intraday day trading) retired: owner can't approve trades within minutes during work hours,
so 3 proposals in 4 days all expired. v2 holds positions 2-10 days so one approval per day is enough.

## Approval flow — AUTO (owner switched on 2026-11-17)
- No approval needed for paper trades. I enter setups that meet these rules and report after.
- Entries: limit orders placed at the 8:17 scan, filled if price trades inside the entry zone that day; unfilled orders cancel at 3:47.
- Every fill and every exit gets a push notification and a chat note with the reason.
- Real-account trades are NOT automatic: those still go to the owner as Webull confirmations, and only after the 30-trade scorecard passes.

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

- **Downtrend reversal — TEMPORARY TRIAL (owner request 2026-11-19)**: liquid names only (price > $5,
  cap > $1B, spread < 0.5%). Stock was below its 50-day MA and 15%+ off its 60-day high. Buy when either
  (A) the close is within 3% of the 60-day low AND 1 signal fires (close above prior high, RSI(14) back
  above 30, or an up day on 1.5x volume), or (B) takeoff: a higher low after the 20-day low, then a close
  above the bounce high on 1.5x volume. Stop just under the low (A: 60-day low, B: the higher low).
  Same 1% risk, 2R target, breakeven at +1R, 10-day time stop.
  Trial status: **FAILED backtest 2026-11-19** (233 trades, 36% win, -0.05R, PF 0.9, -8.6% vs SPY +65.5%,
  DD 12.1%). DISABLED: no paper entries. Kept in code only as an opt-in for future variants.
  Purpose: build the 30+ closed paper trades the Webull risk-sheet.md requires before any live use.
  Remove the setup if the backtest fails.

## Scorecard
**Status 2026-11-19: v2 FAILED backtest — new entries paused pending v3.**
Pass bar (all required): backtest beats SPY after costs with expectancy 95% CI > 0; live paper consistent with backtest; max DD < 8%.

### Old bar (retired: too noisy at 30 trades)
- Pass: expectancy > +0.2R per trade, max drawdown < 8%, profit factor > 1.3.
- Pass = start proposing real-account versions (owner confirms each in Webull).
- Fail = review the rules before continuing.

## Schedule (ET, weekdays)
- 08:17 pre-market scan + proposals (push alert)
- 12:47 midday: fill approved orders, manage stops
- 15:47 close: fill/manage, expire unanswered proposals, daily recap (push)

## Execution venue: Alpaca paper (from 2026-11-18)
- Orders go to the Alpaca PAPER account (…6GSX) via GitHub Actions (`.github/workflows/alpaca-bridge.yml`),
  using the repo secrets ALPACA_KEY_ID / ALPACA_SECRET_KEY. Keys never leave GitHub.
- How: write alpaca/request.json (list of actions), commit, push to this branch; the workflow runs
  alpaca/bridge.py and prints RESULT lines in the job log, which I read back.
- Entries are Alpaca **bracket orders** (limit entry + stop-loss + take-profit held at Alpaca), so stops
  and targets trigger in real time, not at check-ins.
- Inverse ETFs are real symbols on Alpaca (SH, PSQ, SOXS...). Shorting is also enabled, but rules stay long-only.
- Alpaca is the source of truth for fills, cash and P&L; ledger.json mirrors it for the scorecard.
- Paper URL is hard-coded in bridge.py; it cannot reach a live account.
