# Webull rules test (owner) — Kim signal, price <= $15, 50% positions, stops 50%/25%/20% by price tier
10y daily SIP, 348 names, 2016-11-28 to 2026-11-25, start $5,000, 20 bps costs/side (run 46066668626). SPY +278.8%.

| Version | Trades | Win | Avg trade | 95% CI | End | Return | Max drop | Worst losing streak | Biggest loss |
|---|---|---|---|---|---|---|---|---|---|
| A: tier stops + Kim exits | 255 | 37.6% | +3.0% | -1.8..+7.8% | $3,774 | -24.5% | 86% | 11 | -$1,727 |
| B: tier stops only, 60-day hold | 157 | 47.1% | +12.3% | +2.8..+21.7% | $79,792 | +1,496% | 79% | 7 | -$25,577 |
B by year (end balance): 2017 10.4k, 2018 9.7k, 2019 10.2k, 2020 15.9k, 2021 47.7k, 2022 36.5k, 2023 59.3k, 2024 125.1k, 2025 177.5k, 2026 79.8k.
B by tier avg trade: <=$5 +16.3% (62), $5-10 +20.8% (46), $10-15 -0.8% (49). Halves: +14.9% / +10.3% (2nd-half CI -2.7..+23.2).
CAVEATS: strong survivorship bias (universe = today's survivors; cheap stocks that died are missing - worst for the <=$5 tier);
only ~2 positions at a time, so a few trades decide everything; max-drop figures approximate (open positions valued at cost).
