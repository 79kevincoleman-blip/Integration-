# v4.1 pre-registration (written 2026-11-19 BEFORE running)

Hypothesis (from v4 results): high-volume breakouts in relative-strength leaders have a positive edge;
pullbacks and the close<20d exit dragged v4 down.

Exact rules, single variant, no tuning after the run:
- Scan: same as v4 (stocks + index/sector ETFs; 63-day RS vs SPY > 0, top 10; close > 50d > 200d).
- Entry: ONLY high-volume breakout of a 15-30 day base < 12% wide, close > base high on > 1.5x 50-day volume.
  Stop = base midpoint; skip if stop > 2.5 ATR(14). Next-open entry, 5 bps slippage.
- Exit: target 3R; stop; close below the 50-day MA (structure break); 20 trading days max.
- Risk: 1%/trade, 20% max position, 5 positions, 2 per theme, 10% cash floor, cash earns BIL. No regime filter.

Pass (all required, period 2020-11-19..2026-11-18):
1. Avg R > 0 in BOTH halves.
2. Full-period avg R 95% CI lower bound > 0.
3. Beats SPY risk-adjusted (Sharpe > SPY) AND max drawdown < SPY's.
If it passes: paper trade on Alpaca as the out-of-sample test. If it fails: no further variants of this idea.
