"""v3 backtest: index trend-following. Compares variants against SPY buy-and-hold.

Signal on day t close, trade at day t+1 open, 5 bps slippage per switch.
"Cash" is held in BIL (T-bill ETF) so idle money earns the T-bill rate, like a real account would.
"""
import argparse, json, math, os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from backtest import fetch_alpaca, load_csv_dir  # noqa: E402

SLIP = 0.0005


def sma(xs, n, i):
    return sum(xs[i - n + 1:i + 1]) / n if i >= n - 1 else None


VARIANTS = {
    # name: (signal symbol, risk-on asset, risk-off asset, ma length, band)
    "A_spy_200ma_cash": ("SPY", "SPY", "BIL", 200, 0.0),
    "B_spy_200ma_band2_cash": ("SPY", "SPY", "BIL", 200, 0.02),
    "C_spy_200ma_short_SH": ("SPY", "SPY", "SH", 200, 0.02),
    "D_spy_100ma_cash": ("SPY", "SPY", "BIL", 100, 0.01),
    "E_qqq_200ma_cash": ("QQQ", "QQQ", "BIL", 200, 0.02),
}


def run_variant(data, days, sig_sym, on, off, n, band):
    idx = {s: {x["d"]: k for k, x in enumerate(v)} for s, v in data.items()}
    closes = [x["c"] for x in data[sig_sym]]
    held, units, cash, eq, switches = None, 0.0, 100000.0, [], 0
    want_next = None
    for d in days:
        # execute yesterday's decision at today's open
        if want_next and want_next != held:
            ko = idx[want_next].get(d)
            if ko is not None:
                if held:
                    kh = idx[held][d]
                    cash += units * data[held][kh]["o"] * (1 - SLIP)
                px = data[want_next][ko]["o"] * (1 + SLIP)
                units, held, cash = cash / px, want_next, 0.0
                switches += 1
        k = idx[held][d] if held else None
        value = cash + (units * data[held][k]["c"] if held and k is not None else 0)
        eq.append((d, value))
        # decide at today's close
        ks = idx[sig_sym].get(d)
        m = sma(closes, n, ks) if ks is not None else None
        if m is None:
            continue
        c = closes[ks]
        if held != on and c > m * (1 + band):
            want_next = on
        elif held != off and c < m * (1 - band):
            want_next = off
        elif held is None:
            want_next = on if c > m else off
    return eq, switches


def summarize(eq, switches=None):
    vals = [v for _, v in eq]
    peak, mdd = vals[0], 0
    for v in vals:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak)
    yrs = len(vals) / 252
    rets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1))
    out = {"total_return_pct": round((vals[-1] / vals[0] - 1) * 100, 1),
           "cagr_pct": round(((vals[-1] / vals[0]) ** (1 / yrs) - 1) * 100, 2),
           "max_drawdown_pct": round(mdd * 100, 1),
           "sharpe": round(mu / sd * math.sqrt(252), 2) if sd else None}
    if switches is not None:
        out["switches"] = switches
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="3,6")
    ap.add_argument("--csv-dir")
    ap.add_argument("--out", default="backtest_out")
    a = ap.parse_args()
    periods = [float(x) for x in str(a.years).split(",")]
    syms = ["SPY", "QQQ", "SH", "BIL"]
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=int(max(periods) * 365) + 330)
    data = load_csv_dir(a.csv_dir, syms) if a.csv_dir else fetch_alpaca(syms, start.isoformat(), end.isoformat())
    data = {s: sorted(v, key=lambda x: x["d"]) for s, v in data.items() if v}
    results = {}
    for yrs in periods:
        t0 = (end - timedelta(days=int(yrs * 365))).isoformat()
        common = sorted(set.intersection(*[{x["d"] for x in data[s]} for s in syms]))
        days = [d for d in common if d >= t0]
        bh = [(d, data["SPY"][{x["d"]: k for k, x in enumerate(data["SPY"])}[d]]["c"]) for d in days]
        r = {"period": f"{days[0]} to {days[-1]}", "SPY_buy_hold": summarize(bh)}
        for name, spec in VARIANTS.items():
            eq, sw = run_variant(data, days, *spec)
            r[name] = summarize(eq, sw)
        results[f"{yrs:g}y"] = r
    os.makedirs(a.out, exist_ok=True)
    json.dump(results, open(os.path.join(a.out, "summary_v3.json"), "w"), indent=2)
    print("SUMMARY_V3 " + json.dumps(results))
