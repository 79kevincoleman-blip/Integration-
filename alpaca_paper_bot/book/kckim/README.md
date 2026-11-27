# KCkim (separate paper bot, started 2026-11-27)
Owner: "Paper trade B on alpaca, name this KCkim, have it separate from anything else."
Rules = backtest/webull_rules_backtest.py variant W_stop_only (version B):
- Kim-daily buy signal on yesterday's close, stock price <= $15, buy at the open.
- Each position up to 50% of KCkim's balance; never more than KCkim's own cash. Whole shares.
- Fixed stop by entry price: <= $5 -> 50% below; $5.01-$10 -> 25%; $10.01-$15 -> 20%. Never moved.
- Sell after 60 trading days if not stopped.
- Own $5,000 inside the shared Alpaca paper account; own code (bot/kckim_live.py), workflow (alpaca-kckim.yml),
  request file (kckim_request.json), order tags (kc-, kcstop-, kcexit-) and schedule (08:25 + 11:25 ET weekdays).
- Skips a symbol another bot (Kim or the owner) already holds - Alpaca has one position per symbol.
Backtest (10y, $5,000): +1,496% but a 79% worst drop and heavy survivorship bias. This paper run is the real test.
