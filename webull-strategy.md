# Webull strategy: downtrend -> lowest low -> reversal (REAL money)
Applies to the Webull Individual Cash account only. Rules 1-11 in risk-rules.md also apply.
Contains rules only - no account data or credentials.

## 1. Watchlist (what to track)
- Stock is in a downtrend: below its 50-day average AND down 15%+ from its recent high.
- Quality filter: price > $5, market cap > $300M, bid-ask spread < 1% of price.
  (Blocks collapsing penny stocks like IMCC.)
- Check every pick at least 3 times a day (about 10:15 AM, 12:30 PM, 3:00 PM ET).

## 2. Timeframe per stock (set from its history + current news)
- Clean / calm stock (normal daily range, ATR, under 4% of price): use DAILY charts.
- Volatile stock (ATR 4%+ of price, or active news): use INTRADAY 5-15 min charts to time the entry.
- Re-check news on every pick before any buy. Bad news still unfolding = no buy.

## 3. When to buy (strictness: 1 signal)
A. LOWEST-OF-THE-LOWS buy: price is within 3% of the lowest low of the whole downtrend
   (the multi-month low, NOT just today's or yesterday's low)
   AND at least 1 reversal signal:
   - closes above the prior day's high (daily) / prior bar's high (intraday)
   - RSI goes from under 30 back above 30
   - an up move on volume 1.5x+ normal
B. TAKEOFF exception (not at the absolute low): a clear hint of an upward takeoff -
   a higher low that holds, then a break above the last bounce high on 1.5x+ volume.

No signal = keep watching. Never buy just because it is cheap.

## 4. Order
- LIMIT order only, after 10:00 AM ET, at or a little below the current price.
- Stop just under the lowest low (the reversal failed if it breaks). Use rule 3 % if that is tighter.
- Target at least 2x the distance to the stop.
- Size so the stop loses no more than 2% of the account (rule 4).

## 5. Approval
I scan and send the setup (ticker, why, entry, stop, target). An order is created ONLY after
you say yes, and it still needs your confirm tap in the Webull app.
