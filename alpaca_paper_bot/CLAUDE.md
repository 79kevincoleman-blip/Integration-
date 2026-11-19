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
  Backtest of reversal alone requested (backtest/request.json setups=["reversal"]). Paper entries on it
  only if it passes; remove it if it fails. Universe extended with RIVN, F, NU, SOFI, PYPL, SNAP, DIS, INTC, PFE.
- NEW ENTRIES PAUSED per RULES.md (fail = review before continuing). Scheduled tasks only sync/report until owner approves a v3.

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
