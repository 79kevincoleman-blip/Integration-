# Project memory — Alpaca Paper Bot

Read this first when resuming. Owner: repo 79kevincoleman-blip/Integration-, branch claude/webull-paper-trading-lvj9ad.

## Owner preferences
- Direct, concise, no filler. Report what was done and why.
- Wants to be notified by phone push for anything that needs attention; works a day job, can't reply fast.
- Goal: a profitable, proven strategy before any real money.

## Current state (update on every change)
- Mode: AUTO on paper (owner said "Auto" 2026-11-17). Venue: Alpaca paper via GitHub Actions bridge.
- Equity $100,000, 0 positions, 0 closed trades as of 2026-11-18 close.
- Backtest v2 (2026-11-19, 3y, 368 trades): FAIL. +0.031R/trade (95% CI -0.08..+0.14), +6.0% total vs SPY +66.7%, max DD 9.7%.
- 11-19: owner TEMPORARILY added the Webull "downtrend reversal" setup (RULES.md) as a paper trial.
  Backtest of reversal alone: FAIL (233 trades, -0.048R, PF 0.9, -8.6% vs SPY +65.5%, DD 12.1%).
  Setup DISABLED (not in default SETUPS); no paper entries. Universe extended with RIVN, F, NU, SOFI, PYPL, SNAP, DIS, INTC, PFE.
- Backtest v3 trend-following (2026-11-19, 3y+6y, SIP data): no variant beats SPY on return; B (SPY 200d, 2% band, else BIL) cuts DD 24.5%->17% (6y) with similar Sharpe. Awaiting owner decision.
- Backtest v2.1 (2026-11-19, 6y, 283 trades): FAIL. +30% vs SPY +121%. 2020-23 ~SPY with DD 9.9% vs 24.5%; 2023-26 +1.5% vs SPY +68%. Not re-tuned (overfitting risk).
- Backtest v4 (owner outline: RS momentum pullbacks/breakouts, R-multiple or structure exits; 2026-11-19, 6y): FAIL all 4 variants; best +30% vs SPY +121%. Pullbacks negative everywhere; breakouts positive everywhere (+0.09..+0.20R). Candidate next test: breakout-only (pre-declared, post-hoc idea).
- Backtest v4.1 PRE-REGISTERED (breakout-only, 3R, close<50d, 20d max): FAIL 3/4 checks (CI lower -0.07; only 59 trades/6y). +40% vs SPY +121%, Sharpe 1.36 vs 0.88, DD 4.8% vs 24.5%, positive both halves. Best so far. Per prereg: no more variants; owner to decide whether to paper-trade the frozen rules for more data.
- 2026-11-19: owner said 'Let alpaca be fully automated'. v4.1 LIVE on Alpaca paper via bot/live_v41.py + alpaca-live.yml.
  Dry run OK (RS top10 WMT COST DIS AAPL META AMD LLY TSLA ABBV XLP; no signals). Mock tests of entry/exit paths OK.
  Daily run is triggered by the 08:17 ET Claude task pushing live_request.json (cron in the workflow only works once on main).

## Decision log
- 11-12 v1 intraday day trading on a Webull-priced simulated book; Webull orders need owner tap in app.
- 11-12..16 3 proposals expired unanswered (hypothetical +660, -217); approval latency = core problem.
- 11-17 v2 swing (2-10 day holds), inverse ETFs allowed, 1 per theme, 20% cap. Owner chose AUTO.
- 11-18 Alpaca paper connected through GitHub Actions using existing repo secrets (Claude cannot read secrets).
- 11-19 30-trade pass/fail judged too noisy (SE ~0.27R). New bar: backtest beats SPY after costs with
  expectancy CI > 0, live paper consistent with backtest, max DD < 8%.

## Scheduled tasks (Claude remote triggers, this session)
- trig_01NriUq2ctyew3WhxAKn6pkZ  08:17 ET weekdays  pre-market scan + bracket orders
- trig_01GLVo6nSf2d7TTHa93fPb2R  12:47 ET weekdays  midday sync
- trig_01T7CadfzyK4SWSSReYDM6Ws  15:47 ET weekdays  close + recap

- 11-19 Owner added a TEMPORARY reversal-setup trial (from the Webull risk-sheet work on branch
  claude/webull-real-trading-memory-49sdaz). Backtest decides whether it gets paper entries.

## Gotchas
- Webull MCP disconnects often; fall back to Alpaca 'bars' via bridge, then FMP (FMP free plan blocks most ETFs).
- GitHub secret for the secret key may be named ALPACA_SECRET; workflow accepts both.
- Workflow runs only from this branch (push trigger), not main.
