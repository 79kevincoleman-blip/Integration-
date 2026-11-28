# Project memory — Alpaca Paper Bot

Read this first when resuming. Owner: repo 79kevincoleman-blip/Integration-, branch claude/webull-paper-trading-lvj9ad.

## Owner preferences
- Direct, concise, no filler. Report what was done and why.
- Wants to be notified by phone push for anything that needs attention; works a day job, can't reply fast.
- Goal: a profitable, proven strategy before any real money.

## Current state (update on every change)
- 2026-11-25 owner (from the Webull session, branch claude/webull-real-trading-memory-49sdaz) asked for a
  STRUCTURE trial: near own 1y low + fall slowing + 2 higher lows & 2 higher highs. Pre-registered in
  backtest/structure_backtest.py (variants S2, S2_noslow, S1, NEAR baseline; 6y daily). Backtest only; live bot untouched.
  RESULT: FAIL (S2 134 trades +0.183R, CI -0.04..+0.41, both halves +, +13.2% DD 7.8% vs SPY +114%; beats NEAR +0.06R).
  Best per-trade result so far but not significant. Not deployed. results/2026-11-25_structure_6y.md.
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
- v4.1 10-YEAR backtest (2016-26): $100k -> $134.7k (+34.7%, 3.0%/yr, DD 8.4%) vs SPY -> $386.7k (+286.7%). 2016-21 the setup lost (-0.04R); edge only 2021-26. 6y result overstated it.
- 2026-11-28 (Sat) owner test: both bots dry/trial on 11-27 close OK. Kim (paused): would raise stops GILD 166.40->166.58, PLUG 0.81->0.87, TGT 161.84->162.32; no exits. KCkim: 0 signals, $5,000 cash. KCkim got a trial mode.
- 2026-11-27 CLOSE (half day): equity $99,490.66 (+$149 day; -0.51% since start). 10 positions all with GTC stops. Kim 0 closed trades; overall 1 closed (HPQ -0.43R).
- 2026-11-27 owner: 'Pause Kim for now' -> KIM_PAUSED=True in bot/live_v41.py: no new Kim buys; Kim's 7 open positions (ASTS JOBY PATH PLUG GILD TGT DLTR) still managed (GTC stops, trailing, fade/30-day exits) by the 08:15/11:15/13:00 runs. KCkim unaffected. To resume: set KIM_PAUSED=False.
- 2026-11-27 owner: '1. Paper trade B on alpaca, name it KCkim, separate from anything else' -> KCkim built: bot/kckim_live.py, .github/workflows/alpaca-kckim.yml, kckim_request.json, book/kckim/README.md. Own $5,000 sleeve (balance from kc-tagged orders), tags kc-/kcstop-/kcexit-, rules = Webull version B. Kim treats KC positions as not-its-own (left alone) and won't buy a symbol KC holds; KC skips symbols anyone holds. Mock tests OK. Schedule: 08:25 + 11:25 ET weekdays (own tasks: trig_01Uc5xohUzviPJbZdxi5SMMa, trig_01G7FvtbpLbEp1AXYsunKLSh). Real-account dry run OK: KCkim balance $5,000, cash $5,000, 0 positions. First possible buys Mon 2026-11-30 08:25.
- 2026-11-27 WEBULL RULES TEST (owner, $5,000 start): A tier stops+Kim exits: $5k->$3.8k (-24.5%), DD 86%. B tier stops only/60-day hold: $5k->$79.8k (+1,496%, peak $177.5k 2025, -55% in 2026), DD 79%, avg +12.3%/trade CI +2.8..+21.7, $10-15 tier loses. Heavy survivorship bias. Not written to Webull rules yet (owner had not said Y). results/2026-11-27_webull_rules.md.
- 2026-11-27 15:23 HEALTH TEST (owner): bot + bridge OK, account ACTIVE, equity $99,494, 10 positions, Kim scan on 11-27 close = 0 signals. FAIL found: ASTS/JOBY/PATH/PLUG day stop legs expired at 13:00 half-day close -> unprotected. FIXED: protect-only run placed GTC stops (21.74/3.18/11.36/0.81, http 200); code fix: any Kim DAY stop is replaced by a GTC stop at the next run (11:15), not next morning. Mock test OK.
- 2026-11-27 13:00 run skipped (half day, market closed 13:00). Safety fix: Kim entries now require that the market OPENS LATER TODAY (clock.next_open == today), so an after-close run can't queue buys on stale bars.
- 2026-11-27 11:15 run: no exits/signals. Equity $99,278. All 10 positions held by stops (manual qty_available 0 = stops active).
- 2026-11-27 owner: stops on manual buys -> fixed GTC stops (last close - 2.5 ATR14), cid manual-stop-*: MARA 3.61, TNMG 1.69, SKYD 5.47. Not trailed; Kim still ignores manual positions. Bridge action 'stop_atr' added.
- 2026-11-27 10:22 manual run (owner 'run it now'): no exits/signals. Kim buys FILLED: ASTS 174@25.74, JOBY 1034@3.993, PATH 702@12.65, PLUG 2921@1.15; day stop legs active. Equity $99,313; 10 positions (7 Kim, 3 manual).
- 2026-11-27 WEBULL RULES rewritten from this session (owner): branch claude/webull-real-trading-memory-49sdaz commit 03acefc. risk-sheet.md + pretrade.py: strategy = Kim-daily, 1% risk, <=25% per position, never > available cash, max 10 positions, price < $20, penny limits <$5 kept, GO gate kept, paper-first (30 closed Kim paper trades, +R) kept, LIMIT <=2% over prior close at the open, cost <=20% of risk replaces R:R>=2. 12 tests pass. Owner was warned: 25%-risk and 15-min Kim rejected (15-min Kim failed -56%).
- 2026-11-27 08:15 FIRST KIM RUN: adopted GILD (stop 166.40), TGT (161.84), DLTR (140.92) - targets cancelled, GTC stops placed (http 200). Kim buys at open (market OTO + day stop): ASTS 174 sh stop 21.74, JOBY 1034 stop 3.18, PATH 702 stop 11.36, PLUG 2921 stop 0.81 (~$745 risk each). Equity $99,345. Half day (close 13:00). VERIFIED 08:19: exactly one GTC stop each GILD/TGT/DLTR; 4 OTO buys queued (day stop legs expire at 13:00 close; Monday 08:15 run places GTC stops).
- 2026-11-27 owner: 'start with Kim exact rules only, taking over anything there already' -> (1) 10% drawdown halt REMOVED (not in Kim's test); (2) Kim ADOPTS old v42 positions GILD/TGT/DLTR: initial stop = their original bracket stop, entry = fill price/date; first run cancels their take-profit/OCO orders and places Kim's GTC trailing stop; Kim's fade/30-day exits apply. Owner chose: manual MARA/TNMG/SKYD stay untouched. Mock test OK.
- 2026-11-26 owner 'Run on crypto paper' -> tested first: Kim-crypto (frozen rules, 26 pairs, 2021-26) FAIL: 178 trades -0.085R, -12.3%, both halves negative (BTC hold +4.4%). Not deployed. results/2026-11-26_kim_crypto.md.
- 2026-11-26 08:15 run: Thanksgiving, market closed; bot exited immediately (no orders).
- 2026-11-25 CLOSE: equity $99,341.54 (day -$702; -0.66% since start vs SPY +0.13% since 11-19 close). HPQ closed -$227.64 (-0.43R; sold @30.27). Open bot: GILD -$30, TGT -$236, DLTR -$167 (all GTC stop+target). Manual MARA +$5, SKYD -$1, TNMG -$3. 4 entries / 1 closed. Bridge 'bars' now accepts start date.
- 2026-11-25 KIM-DAILY RESULT: KD_nohist PASSES pre-reg (981 trades, +0.214R CI +0.09..+0.34, both halves +). Uncapped +332% vs SPY +280%; no-leverage (12.5% cap) +245%, DD 20.8%; 7/10 years positive. History filter (35%/50%) does NOT help. Caveat: survivorship bias. OWNER CHOSE: Kim replaces v4.3 for new entries (2026-11-25). Live: bot/kim_live.py wired into live_v41.py (ENTRIES='kim'). Kim buys only in the 8:15 pre-market run (market OTO buy + day stop; later runs set GTC stop and trail it up; exits on momentum fade / 30 days). Tag kd-SYM-YYYYMMDD-s<stopcents>. v4.3 (v42-) positions GILD/TGT/DLTR still managed to exit. (halt rule removed 11-27.) Mock test OK. Real-data dry run 2026-11-25 OK (349 prices; would have flagged PATH, PINS on 11-24 close; no orders). Thu 11-26 Thanksgiving = closed; first possible Kim buys Fri 11-27 08:15 run (half day).
- 2026-11-25 owner 'Yes' -> Kim-DAILY one-shot 10y test (backtest/kim_daily.py, frozen rules, variants nohist/hist35/hist50). No re-tuning after it.
- 2026-11-25 13:00 run: EXIT HPQ (market sell 271) structure-break: live price 30.25 < 50d MA only ~95 min after entry @31.11; ~-$234 (-0.44R). FIRST CLOSED TRADE. ISSUE: live bot tests the 50d exit on the INTRADAY price (overlay), backtest tests it on the daily CLOSE -> intraday whipsaw exits. FIXED (owner 'Uea'=yes): structure exit now uses completed daily closes only (today's in-progress bar excluded); mock test OK. Stops/targets unchanged. Equity $99,439.
- 2026-11-25 11:15 run (ran 11:39, GitHub 503 outage ~16:16-16:39 UTC): entry HPQ 271 sh limit 31.19 stop 29.14 tgt 37.34 (GTC bracket). Equity $99,607 (TGT -$261, DLTR -$118). 4/30 entries. Another session pushed a 'structure trial' backtest (FAIL, not deployed) to this branch; merged.
- 2026-11-25 08:15 run (v4.3): OK, no exits, no new signals. Equity $100,084.54; 6 positions (3 bot w/ GTC stops, 3 manual).
- 2026-11-25 KIM run 2 (owner: 35% bounce record): FAIL. hist35 432 trades -0.176R (worse than no filter), -31.9%; hist40 68 trades -0.092R, -3.1%. Not deployed.
- 2026-11-25 KIM 2y RESULT: FAIL. 16,705 downtrend events, only 30.7% reversed. No-history version: 1,431 trades, -0.112R (CI -0.16..-0.06), -56%, DD 60.5%, negative both halves. History-filter versions: 0 trades (no stock reversed >=50% of the time). Not deployed. results/2026-11-25_kim_2y.md.
- 2026-11-25 owner asked for 'Kim': intraday (15-min) downtrend-reversal bot using each stock's own reversal history; auto-buy on paper; volatile small caps included. Pre-registered in backtest/kim_backtest.py (3 variants, 2y SIP). Not live until it passes AND owner says go. Note: live intraday needs runs every 15 min -> GitHub cron on main (owner permission needed).
- 2026-11-24 16:20 protect run OK: GTC OCO stop+target now live for GILD (166.17/212.29) and TGT (161.45/219.93); DLTR GTC bracket live. All 3 bot positions protected.
- 2026-11-24 CLOSE: equity $100,043.54 (+$43.54 day). GILD +$111, TGT +$8, DLTR -$74; manual MARA +$4, SKYD -$1, TNMG -$4. 0 closed trades; 3/30 entries. GILD/TGT day-legs expired at close (confirmed no open orders); 16:20 protect run re-arms them.
- 2026-11-24 13:00 run: no exits/signals. DLTR FILLED @155.83 (GTC stop/target). Equity $100,080; bot positions GILD, TGT, DLTR (3/30 live trades); manual MARA, SKYD, TNMG.
- 2026-11-24 11:25 first v4.3 run: entry DLTR 46 sh limit 155.96 stop 139.69 tgt 204.77 (GTC bracket). Manual MARA/SKYD/TNMG left alone. Equity $100,053.
- 2026-11-24 owner: 'Switch to C and run that' -> v4.3 LIVE: backtest/strategy_v43.py (C_slots: 12 pos, 0.75% risk, 8.5% cap, 4/sector, 5 new/day). Signals unchanged. Order tag stays 'v42-' so GILD/TGT stay bot-managed.
- 2026-11-24 owner MANUAL paper buys (market, 15 sh each): MARA, TNMG, SKYD (client_order_id manual-*). Bot ignores manual positions (manages only v42-tagged buys). No stops on manual buys unless owner asks.
- 2026-11-24 BUG FIX: bracket legs were TIF 'day' -> stop/target expire at close. Bot now (a) re-places a GTC OCO stop+target for any held position lacking one (from our entry order's legs), (b) enters with GTC brackets, (c) cancels our unfilled entries from earlier days. Added protect_only request flag. Execution fix only; strategy rules unchanged.
- 2026-11-24 11:15 live run: FIRST ENTRIES (both FILLED: GILD @177.17, TGT @175.69; equity $100,006). GILD 70 sh limit 177.70 stop 166.17 tgt 212.29; TGT 68 sh limit 176.07 stop 161.45 tgt 219.93 (bracket orders). Missed (session restart): 11-23 11:15/13:00/16:00 and 11-24 08:15.
- 2026-11-23 08:15 live run (v4.2, pre-market): OK, 309 prices, no exits, no breakout signals, 0 orders. Equity $100,000, 0 positions.
- 2026-11-21 v4.3 'more trades' 10y test (backtest_v43.py, results/2026-11-21_v43_10y.md): no variant passes pre-declared rule. Best = C_slots (12 pos, 0.75% risk, 8.5% cap, 4/sector, 5 new/day): 112 trades/yr, +0.103R CI>0, +63.9%, DD 12.3% vs live v42 (top100) 93/yr, +0.088R, +60.5%, DD 18.9%. SPY +264.6%. Awaiting owner Y/N to switch live to C.
- 2026-11-21 (Sat) trials: Alpaca bridge + live bot trial mode OK (309 prices, top-100 RS, no breakouts on Fri close). Webull connector read-only check OK. Added 'trial' flag (dry run on closed days).
- 2026-11-20 close: day 1 of v4.2 done. 4 runs (08:15, 09:36, 11:15, 13:00), 0 signals, 0 orders. Equity $100,000, 0 positions, 0/30 live trades.
- 2026-11-20: owner: 'Run again and expand to 100 names' -> RS candidate list top 100 (was 20). Universe still 308.
- 2026-11-20 08:15 first v4.2 live run: OK, no signals, no orders. Equity $100,000, 0 positions.
- v4.2 10y backtest (run after go-live): 257 trades but $100k->$112.5k vs v4.1 $134.7k; avg -0.05R, negative both halves. Owner informed; v4.2 still live per owner unless told otherwise.
- 2026-11-19 night: owner: 'Do all 4 changes and let's see how it does on paper tomorrow' -> v4.2 LIVE from 2026-11-20
  (backtest/strategy_v42.py, client_order_id tag v42-). Dry run OK: 309 live prices, no signals. Fixed SIP 403 (explicit UTC end).
- 2026-11-19 evening: owner: KEEP RUNNING v4.1 on paper; wants future tweaks to make MORE trades (test before changing live).
- 2026-11-19: owner said 'Let alpaca be fully automated'. v4.1 LIVE on Alpaca paper via bot/live_v41.py + alpaca-live.yml.
  Dry run OK (RS top10 WMT COST DIS AAPL META AMD LLY TSLA ABBV XLP; no signals). Mock tests of entry/exit paths OK.
  2026-11-19: owner: decide on real-time prices, not prior close. Bot now uses live IEX last trade + today's partial bar
  (15-min delayed SIP, volume projected) during market hours; pre-market skips >1% gaps, limit = live +0.3%.
  NOTE: live rules now differ from the backtest (which decided at close, entered next open).
  Bot trades at 08:15, 11:15, 13:00; 16:00 is recap only.
  Daily run is triggered by the 08:17 ET Claude task pushing live_request.json (cron in the workflow only works once on main).

## Decision log
- 11-12 v1 intraday day trading on a Webull-priced simulated book; Webull orders need owner tap in app.
- 11-12..16 3 proposals expired unanswered (hypothetical +660, -217); approval latency = core problem.
- 11-17 v2 swing (2-10 day holds), inverse ETFs allowed, 1 per theme, 20% cap. Owner chose AUTO.
- 11-18 Alpaca paper connected through GitHub Actions using existing repo secrets (Claude cannot read secrets).
- 11-19 30-trade pass/fail judged too noisy (SE ~0.27R). New bar: backtest beats SPY after costs with
  expectancy CI > 0, live paper consistent with backtest, max DD < 8%.

## Scheduled tasks (Claude remote triggers, this session; weekdays ET, from 2026-11-20)
- trig_01NriUq2ctyew3WhxAKn6pkZ  08:15  live v4.1 run (orders + exits) via live_request.json
- trig_01GLVo6nSf2d7TTHa93fPb2R  11:15  fills/positions check (read-only)
- trig_01DjiAsqLDt66HZYq2QgYJDQ  13:00  fills/positions check (read-only)
- trig_01T7CadfzyK4SWSSReYDM6Ws  16:00  close recap + push
- trig_01Uc5xohUzviPJbZdxi5SMMa  08:25  KCkim run (separate bot)
- trig_01G7FvtbpLbEp1AXYsunKLSh  11:25  KCkim stop check

- 11-19 Owner added a TEMPORARY reversal-setup trial (from the Webull risk-sheet work on branch
  claude/webull-real-trading-memory-49sdaz). Backtest decides whether it gets paper entries.

## Gotchas
- Webull MCP disconnects often; fall back to Alpaca 'bars' via bridge, then FMP (FMP free plan blocks most ETFs).
- GitHub secret for the secret key may be named ALPACA_SECRET; workflow accepts both.
- Workflow runs only from this branch (push trigger), not main.
