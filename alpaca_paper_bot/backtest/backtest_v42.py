"""Backtest of v4.2 (strategy_v42 changes on top of v4.1). Reuses backtest_v41's runner; output label 'v4_1' = this run."""
import os, sys, runpy
sys.path.insert(0, os.path.dirname(__file__))
import strategy_v42  # noqa: E402,F401  patches backtest_v4 before backtest_v41 wraps it
runpy.run_path(os.path.join(os.path.dirname(__file__), "backtest_v41.py"), run_name="__main__")
