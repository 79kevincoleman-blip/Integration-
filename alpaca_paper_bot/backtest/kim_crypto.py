"""KIM-CRYPTO — owner 2026-11-26 "Run on crypto paper". Same frozen Kim-daily rules (kim_daily.py, KD_nohist) on
Alpaca's crypto pairs, daily bars (crypto trades 7 days a week, so "days" are calendar days). Only change: slippage
20 bps per side (crypto spreads are wider). PASS = same checks as Kim-daily: avg R 95% CI low > 0, both halves > 0,
return > 0. Also reported vs buy-and-hold BTC. No re-tuning after this run.
"""
import argparse, json, os, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(__file__))
import kim_daily as kd  # noqa: E402

kd.SLIP = 0.0020
PAIRS = ("BTC ETH SOL LTC BCH LINK UNI AAVE AVAX DOGE SHIB DOT XRP MKR GRT CRV SUSHI YFI BAT XTZ PEPE TRUMP "
         "ADA ARB ONDO RENDER HBAR SUI").split()


def fetch(start, end):
    key, sec = os.environ.get("ALPACA_KEY_ID", "").strip(), os.environ.get("ALPACA_SECRET_KEY", "").strip()
    out = {}
    syms = [p + "/USD" for p in PAIRS]
    token = None
    while True:
        q = {"symbols": ",".join(syms), "timeframe": "1Day", "start": start, "end": end, "limit": 10000}
        if token:
            q["page_token"] = token
        req = urllib.request.Request("https://data.alpaca.markets/v1beta3/crypto/us/bars?" + urllib.parse.urlencode(q),
                                     headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    js = json.loads(r.read().decode())
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise SystemExit(f"crypto bars error {e.code} {e.read().decode()[:300]}")
        for s, bars in (js.get("bars") or {}).items():
            out.setdefault(s, []).extend({"d": b["t"][:10], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                                          "v": b["v"]} for b in bars)
        token = js.get("next_page_token")
        if not token:
            break
    return {s: sorted(v, key=lambda x: x["d"]) for s, v in out.items() if len(v) > 120}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--years", default="6"); ap.add_argument("--out", default="out")
    a = ap.parse_args()
    yrs = float(str(a.years).split(",")[-1])
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=int(yrs * 365))
    data = fetch(f"{start.isoformat()}T00:00:00Z", f"{end.isoformat()}T23:59:00Z")
    btc = data["BTC/USD"]
    t0 = btc[120]["d"]  # first 120 days only warm up indicators
    days = [x["d"] for x in btc if x["d"] >= t0]
    mid = days[len(days) // 2]
    P = {"full": (days[0], days[-1]), "first_half": (days[0], mid), "second_half": (mid, days[-1])}
    pre = {s: (b, kd.ind(b)) for s, b in data.items()}
    evs = {s: kd.events(b, k) for s, (b, k) in pre.items()}
    allev = [e for v in evs.values() for e in v]

    def btc_ret(t_a, t_b):
        c0 = next(x["c"] for x in btc if x["d"] >= t_a)
        c1 = [x["c"] for x in btc if x["d"] <= t_b][-1]
        return round((c1 / c0 - 1) * 100, 1)
    res = {"periods": {k: f"{v[0]} to {v[1]}" for k, v in P.items()}, "pairs_loaded": sorted(data),
           "first_bar_per_pair": {s: b[0]["d"] for s, b in data.items()},
           "events_total": len(allev), "event_reversal_rate_all": round(sum(e["rev"] for e in allev) / max(1, len(allev)), 3),
           "BTC_buy_hold_pct": {k: btc_ret(*v) for k, v in P.items()}}
    cand = [t for s, (b, k) in pre.items() for t in kd.trades(s, b, k, evs[s], None) if t["in"] >= t0]
    taken, curve = kd.simulate(cand, cap=0.125)
    res["KC"] = {k: kd.stats(taken, curve, *v) for k, v in P.items()}
    f, h1, h2 = res["KC"]["full"], res["KC"]["first_half"], res["KC"]["second_half"]
    res["verdict"] = {"ci_low_pos": f.get("avg_r_95ci", [-1])[0] > 0,
                      "both_halves_pos": h1.get("avg_r", -1) > 0 and h2.get("avg_r", -1) > 0,
                      "return_pos": f.get("return_pct", -1) > 0}
    res["verdict"]["PASS"] = all(res["verdict"].values())
    res["by_pair"] = {s: {"trades": sum(t["sym"] == s for t in taken),
                          "avg_r": round(sum(t["r"] for t in taken if t["sym"] == s) / max(1, sum(t["sym"] == s for t in taken)), 3)}
                      for s in sorted({t["sym"] for t in taken})}
    os.makedirs(a.out, exist_ok=True)
    json.dump({"summary": res, "trades": taken}, open(os.path.join(a.out, "kim_crypto.json"), "w"), indent=1)
    print("SUMMARY_KIMC " + json.dumps(res))
