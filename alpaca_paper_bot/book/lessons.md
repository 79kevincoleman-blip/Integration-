# Webull paper book lessons

## 2026-11-12
- AMD relative-strength setup vs NVDA CEO selloff worked (+1.07R hypothetical) but expired twice unanswered. Approval latency, not the read, was the failure. Fix: earlier alerts with longer validity windows.
- Without Webull data, FMP free quotes were unreliable midday (bid/ask $50 wide). No trades on bad data.

## 2026-11-13
- Watchlist condition (AMD hold >575 and break 594) kept the book out of a -8.8% day. Conditional entries > predictions.

## 2026-11-16
- AMD reclaim of 520 failed within 5 minutes after a 9:46 "US tightens AI chip export rules" headline. Rule added: a fresh sector-negative headline in the 15 min before entry voids the long setup.

## 2026-11-17 — switched to v2 swing
- v1 intraday: 0 trades in 4 sessions; 3 proposals expired unanswered (hypothetical +0.07R net over 2). Approval latency made intraday impossible. v2 holds 2-10 days with one approval per day.

## 2026-11-18
- NVDA beat faded: SMH opened 468, closed ~458; SPY never bounced (high 735 vs 748 trigger). In a strong downtrend, waiting for a bounce into the 20d can miss the move. Add alternative trigger: continuation entry on a break of the prior day low.

## 2026-11-19 — backtest
- v2 rules on 3y of daily data: 368 trades, +0.03R avg, no statistically real edge; +6% vs SPY +67%. Risk control worked (DD 9.7% vs SPY 18.7%) but there is no profit engine. Paused per rules.

## 2026-11-19 — reversal trial
- Webull "downtrend -> lowest low -> reversal" setup on 3y of liquid names: 233 trades, 36% win, -0.05R, -8.6% vs SPY +65.5%. Buying the bottom of downtrends loses even in liquid stocks; the IMCC/BGSF losses were the strategy, not just the stock picks. Disabled.

## 2026-11-19 — v2.1 repair attempt
- Regime filter + momentum ranking + trailing exits + T-bill cash: worked in 2020-23 (near SPY, far smaller drawdown), failed in 2023-26 (+1.5% vs +68%). A fix that only works in one half is luck, not an edge. 13% of trades gapped through stops.

## 2026-11-19 — v4 (owner momentum outline)
- 4 variants, 6y: all fail (best +30% vs +121%). Pullbacks lose in every version; high-volume breakouts make money in every version. 41% of exits were the close-below-20d rule, probably too tight for "days to weeks" trends.

## 2026-11-19 — v4.1 (pre-registered breakout-only)
- First version with positive results in both halves and far smaller drawdown (4.8%) than SPY (24.5%). Failed only the statistical-certainty check: 59 trades is too few. Most money sat in T-bills, so raw return is low (+40% vs +121%).
