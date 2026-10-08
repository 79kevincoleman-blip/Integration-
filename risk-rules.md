# Risk rules (the seatbelt) - the bot cannot override these
1. Position size: 10-15% of account normally. Up to 30% only for a high-conviction temporary-dip buy, and only ONE 30% position at a time. Scale in: ~1/3 first, add only if it stabilizes.
2. Max 8 open positions. Keep at least 10% cash.
3. Every buy gets a stop immediately: 15% (price under $100), 20% ($100-$1,000), 10% ($1,000+, no news). Stops are sized to the stock's normal daily range (ATR) when that is wider.
4. Never risk more than ~2% of the account on one trade (shrink the share count to fit).
5. Trailing stop once a trade is +15%: sell if price falls 7% from its peak (10% for very volatile stocks/crypto).
6. No averaging down on a loser. Add only if the original reason still holds and price has stabilized.
7. Pause-and-review at -30% of the starting $5,000: stop trading, write what went wrong.
8. Before each trade: read journal.csv; skip or shrink setups similar to past losers.
9. Do not chase: skip a stock that has already spiked more than ~10% today without a pullback.
