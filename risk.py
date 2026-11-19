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
    # Size by risk only (rule 1): dollars at risk / stop distance. No % position caps.
    dollars = VIRTUAL_CAPITAL * MAX_RISK_PER_TRADE_PCT / stop_pct
    spendable = cash - VIRTUAL_CAPITAL * MIN_CASH_PCT
    dollars = min(dollars, spendable)
    if dollars <= 0:
        return 0.0
    return round(dollars / price, 4)


def should_pause(equity_virtual):
    return equity_virtual <= VIRTUAL_CAPITAL * (1 - PAUSE_DRAWDOWN_PCT)


NO_BUY_UNTIL_ET = (10, 0)      # no buys before 10:00 AM ET
MIN_PULLBACK_PCT = 0.03        # limit must be >= 3% under last price, unless at/below VWAP or support


def buy_order_allowed(order_type, et_hour, et_minute, limit_price, last_price,
                      vwap=None, support=None):
    """Rules 10-11: limit orders only, not in the first 30 min, and only at a low point."""
    if order_type.upper() != "LIMIT" or limit_price is None:
        return False
    if (et_hour, et_minute) < NO_BUY_UNTIL_ET:
        return False
    at_low = limit_price <= last_price * (1 - MIN_PULLBACK_PCT)
    if vwap is not None and limit_price <= vwap:
        at_low = True
    if support is not None and limit_price <= support:
        at_low = True
    return at_low
