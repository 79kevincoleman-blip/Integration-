# STRUCTURE trial (owner) — 6y daily SIP, 86 names, 2020-11-26 to 2026-11-25 (run 45629035820)
Pre-registered in backtest/structure_backtest.py. SPY buy-and-hold over the same period: +114.3%.

| Variant | Trades | Win | Avg R | 95% CI | 1st half | 2nd half | Return | Max DD | Pass |
|---|---|---|---|---|---|---|---|---|---|
| S2 (low + slowing + 2HL/2HH) | 134 | 41.8% | +0.183 | -0.042..+0.408 | +0.107 | +0.240 | +13.2% | 7.8% | no (CI includes 0) |
| S2_noslow | 184 | 36.4% | +0.072 | -0.113..+0.258 | +0.051 | +0.087 | +7.0% | 8.4% | no |
| S1 (1HL/1HH) | 497 | 31.8% | -0.025 | -0.158..+0.107 | +0.040 | -0.078 | -1.1% | 15.2% | no |
| NEAR baseline | 1,299 | 32.7% | +0.060 | -0.011..+0.132 | +0.060 | +0.061 | +44.7% | 21.6% | (baseline) |

Verdict per pre-registration: FAIL (no variant has CI lower bound > 0). Not deployed. No re-tuning.
Notes: S2 is the best per-trade result of any setup tested so far, positive in both halves, and beats the
baseline - the 2HL/2HH structure and the "fall slowing" filter each added edge. But 134 trades (~22/yr) is
too few to rule out luck, and total return is far below SPY. Next honest step if the owner wants it:
paper-trade the FROZEN S2 rules forward for out-of-sample data (as with v4.1).
