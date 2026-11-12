# Webull Paper Day-Trading Book ($100,000 virtual)

Separate from the Alpaca project. Prices come from live Webull market data; no orders are sent to Webull.
The ledger (`ledger.json`) is the source of truth. Every decision is logged in `journal.csv`.

## Approval flow
- Every new entry is a **proposal**: symbol, side, limit entry, stop, target, shares, reason.
- Owner gets a push alert and replies **Y** (confirm) or **N** (reject). `Y 2` / `N 1` for a specific proposal.
- No answer before the next check-in = proposal expires. Nothing is traded without a Y.
- Exits (stop, target, end-of-day flatten) are pre-approved as part of the confirmed trade and run without asking.

## Risk (hard limits)
1. Risk per trade = 1% of equity at proposal time (`(entry - stop) * shares`).
2. Max position notional 25% of equity. Max 4 open positions. No leverage, no shorting (long stocks only).
3. Daily loss limit -3% of start-of-day equity: stop proposing for the rest of the day.
4. Weekly drawdown -6%: halve risk to 0.5% until a new equity high.
5. Day trading: everything is flat by 15:55 ET. No overnight holds.
6. Universe: US common stocks, price >= $10, avg daily volume >= 2M, no stocks halted or up >25% without a pullback.
7. Minimum reward:risk 2:1 to the first target.

## Fill simulation (conservative)
- Buy limit fills only if a 5-minute bar after confirmation trades at or below the limit; fill = limit + $0.01.
- Stop fills at stop - $0.01 (gap through = bar open). Target fills at target.
- If stop and target both inside the same bar, assume the stop hit first.
- After +1R, stop moves to breakeven.

## Setups
- **ORB-VWAP pullback**: gapper with catalyst and RVOL > 2, holds above VWAP after the opening range, buy the pullback to VWAP/ORH, stop below the pullback low.
- **Relative-strength trend**: stock green while SPY red, higher lows on 5-min, buy the break of the midday range, stop under the range.
- **Failed-breakdown reclaim**: liquid large cap flushes below a key level then reclaims it on volume, stop under the flush low.

## Schedule (ET, weekdays)
09:50, 11:50, 13:50 scan/manage · 15:50 manage + flatten · 16:17 daily recap.
