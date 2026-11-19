"""v4.1: breakout-only, 3R target, close<50d structure exit. Rules frozen in V4_1_PREREGISTRATION.md."""
import json, math, os, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(__file__))
import backtest_v4 as v4  # noqa: E402

_orig_signal = v4.entry_signal


def breakout_only(b, i):
    s = _orig_signal(b, i)
    return s if s and s[0] == "breakout" else None


v4.entry_signal = breakout_only
_orig_sma = v4.sma


def run(data, days):
    # swap the 20-day structure MA for the 50-day by patching sma calls with n == 20 inside exits only
    def sma_patch(xs, n, i):
        return _orig_sma(xs, 50 if n == 20 else n, i)
    v4.sma = sma_patch
    try:
        return v4.run(data, days, 3.0, False)
    finally:
        v4.sma = _orig_sma


def sharpe(eq, t0, t1):
    vals = [v for d, v in eq if t0 <= d <= t1]
    r = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    mu = sum(r) / len(r)
    sd = math.sqrt(sum((x - mu) ** 2 for x in r) / (len(r) - 1))
    return round(mu / sd * math.sqrt(252), 2)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--years", default="6"); ap.add_argument("--csv-dir"); ap.add_argument("--out", default="out")
    a = ap.parse_args()
    yrs = float(str(a.years).split(",")[-1])
    syms = sorted(set(v4.NAMES) | {v4.BENCH, v4.CASHETF})
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=int(yrs * 365) + 330)
    data = v4.load_csv_dir(a.csv_dir, syms) if a.csv_dir else v4.fetch_alpaca(syms, start.isoformat(), end.isoformat())
    data = {s: sorted(v, key=lambda x: x["d"]) for s, v in data.items() if v}
    t0 = (end - timedelta(days=int(yrs * 365))).isoformat()
    bil = {y["d"] for y in data[v4.CASHETF]}
    days = [x["d"] for x in data[v4.BENCH] if x["d"] >= t0 and x["d"] in bil]
    mid = days[len(days) // 2]
    P = {"full": (days[0], days[-1]), "first_half": (days[0], mid), "second_half": (mid, days[-1])}
    tr, eq = run(data, days)
    spy_eq = [(x["d"], x["c"]) for x in data[v4.BENCH] if x["d"] in set(days)]
    res = {"periods": {k: f"{v[0]} to {v[1]}" for k, v in P.items()},
           "SPY": {k: {**v4.spy_stats(data, *v), "sharpe": sharpe(spy_eq, *v)} for k, v in P.items()},
           "v4_1": {k: v4.summarize(tr, eq, data, *v) for k, v in P.items()}}
    f, h1, h2 = res["v4_1"]["full"], res["v4_1"]["first_half"], res["v4_1"]["second_half"]
    checks = {"avg_r_pos_both_halves": h1.get("avg_r", -1) > 0 and h2.get("avg_r", -1) > 0,
              "full_ci_low_pos": f.get("avg_r_95ci", [-1])[0] > 0,
              "sharpe_beats_spy": (f.get("sharpe") or -9) > res["SPY"]["full"]["sharpe"],
              "dd_below_spy": f["max_dd_pct"] < res["SPY"]["full"]["max_dd_pct"]}
    res["prereg_checks"] = checks
    res["verdict"] = "PASS" if all(checks.values()) else "FAIL"
    os.makedirs(a.out, exist_ok=True)
    json.dump({"summary": res, "trades": tr}, open(os.path.join(a.out, "v41.json"), "w"), indent=1)
    print("SUMMARY_V41 " + json.dumps(res))
