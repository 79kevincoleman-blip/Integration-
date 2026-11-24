"""v4.3 = v4.2 signals + 'C_slots' sizing (owner chose C on 2026-11-24; see results/2026-11-21_v43_10y.md).
12 positions, 0.75% risk per trade, 8.5% max per position, 4 per sector, 5 new per day.
Signals, universe, RS top 100, stops, 3R target, 50d structure exit, 20-day time stop: unchanged from v4.2."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import strategy_v42  # noqa: E402,F401  patches backtest_v4 with v4.2 rules
import backtest_v4 as v4  # noqa: E402

v4.MAX_POS = 12
v4.RISK = 0.0075
v4.CAP = 0.085
v4.PER_THEME = 4
MAX_NEW = 5
