"""Risk manager: the seatbelt. Pure math, no network."""
from config import *


def stop_pct_for_price(price, atr_pct=0.0, no_news=False):
    """15% under $100, 20% for $100-$1000, 10% above $1000 (no news). Widen to ATR if larger."""
    if price < 100:
        base = 0.15
    elif price < 1000:
        base = 0.20
    else:
        base = 0.10 if no_news else 0.20
    return max(base, atr_pct)


def shares_to_buy(price, stop_pct, open_positions, cash, high_conviction_dip=False,
                  have_big_position=False):
    """Return share count (fractional ok) or 0 if any rule blocks the trade."""
    if open_positions >= MAX_POSITIONS:
        return 0.0
    size_pct = NORMAL_POSITION_PCT
    if high_conviction_dip and not have_big_position:
        size_pct = MAX_DIP_POSITION_PCT
    dollars = VIRTUAL_CAPITAL * size_pct
    dollars = min(dollars, VIRTUAL_CAPITAL * MAX_RISK_PER_TRADE_PCT / stop_pct)
    spendable = cash - VIRTUAL_CAPITAL * MIN_CASH_PCT
    dollars = min(dollars, spendable)
    if dollars <= 0:
        return 0.0
    return round(dollars / price, 4)


def should_pause(equity_virtual):
    return equity_virtual <= VIRTUAL_CAPITAL * (1 - PAUSE_DRAWDOWN_PCT)
