"""v4.2 = v4.1 + owner's 4 'more trades' changes (2026-11-19). Importing this module patches backtest_v4.

1. Bigger universe: ~300 liquid US large caps + index/sector ETFs (was ~60). Themes = sectors.
2. Relative-strength list: top 20 (was 10).
3. Looser breakout: base up to 15% wide (was 12%), volume >= 1.3x 50-day avg (was 1.5x).
4. Up to 8 positions (was 5), each max 12.5% of equity (was 20%); 3 per sector (was 2); 3 new per day (was 2).
Unchanged: RS > SPY over 63 days, close > 50d > 200d, stop = base midpoint (skip if > 2.5 ATR),
3R target, exit on close < 50d or after 20 trading days, 1% risk per trade, 10% cash floor.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import backtest_v4 as v4  # noqa: E402

SECTORS = {
    "tech": "AAPL MSFT NVDA AVGO ORCL CRM ADBE AMD CSCO ACN IBM INTU NOW QCOM TXN AMAT MU LRCX ADI KLAC PANW "
            "SNPS CDNS ANET CRWD FTNT MRVL INTC DELL HPQ HPE NXPI MCHP ON MPWR WDAY ADSK TEAM DDOG ZS SNOW NET "
            "PLTR SHOP APP SMCI STX WDC KEYS GLW TER ARM TSM ASML",
    "comm": "GOOGL META NFLX DIS CMCSA T VZ TMUS CHTR EA TTWO WBD SPOT RBLX PINS SNAP TTD",
    "consumer": "AMZN TSLA HD MCD NKE LOW SBUX TJX BKNG CMG ORLY AZO ROST MAR HLT ABNB YUM DHI LEN GM F "
                "LULU DECK RCL CCL UBER DASH EBAY ETSY DPZ ULTA BBY RIVN",
    "staples": "WMT COST PG KO PEP PM MO MDLZ CL KMB GIS KHC STZ KR TGT DG DLTR MNST HSY SYY",
    "health": "LLY UNH JNJ ABBV MRK PFE TMO ABT DHR AMGN ISRG BMY GILD VRTX REGN SYK BSX MDT CVS CI ELV "
              "HCA ZTS MCK BDX IDXX DXCM MRNA BIIB HUM IQV",
    "financials": "JPM BAC WFC GS MS C SCHW BLK AXP SPGI CB PGR MMC ICE CME USB PNC TFC COF AIG MET PRU "
                  "BK TRV AFL ALL KKR BX APO PYPL XYZ COIN HOOD SOFI NU V MA",
    "industrials": "CAT GE HON UNP UPS RTX LMT BA DE ETN ITW EMR NOC GD CSX NSC FDX WM MMM PH TT CARR "
                   "JCI PCAR CMI ROK URI FAST ODFL DAL UAL AAL LUV GEV VRT PWR AXON",
    "energy": "XOM CVX COP EOG SLB OXY PSX MPC VLO WMB KMI OKE HAL DVN FANG HES BKR CTRA",
    "materials": "LIN SHW APD ECL FCX NEM DOW DD NUE ALB MLM VMC CF MOS",
    "utilities": "NEE DUK SO D AEP EXC SRE XEL PCG ED CEG VST NRG",
    "realestate": "PLD AMT EQIX CCI PSA O SPG WELL DLR VICI",
}
ETFS = {"QQQ": "etf-index", "IWM": "etf-index", "DIA": "etf-index", "XLK": "etf-tech", "SMH": "etf-tech",
        "XLE": "etf-energy", "XLF": "etf-fin", "XLV": "etf-health", "XLI": "etf-ind", "XLY": "etf-cons",
        "XLP": "etf-staples", "XLU": "etf-util", "XLB": "etf-mat", "XLRE": "etf-re", "XLC": "etf-comm",
        "GLD": "etf-gold", "SLV": "etf-silver", "TLT": "etf-bonds", "IBB": "etf-health", "KRE": "etf-fin",
        "XBI": "etf-health", "ITB": "etf-cons", "XHB": "etf-cons", "ARKK": "etf-tech"}
NAMES = {s: sec for sec, ss in SECTORS.items() for s in ss.split()}
NAMES.update(ETFS)

BASE_MAX_WIDTH, VOL_MULT = 0.15, 1.3


def entry_signal(b, i):
    """High-volume breakout only (v4.1 logic) with v4.2 thresholds."""
    if i < 200:
        return None
    c = [x["c"] for x in b]
    s50, s200, a = v4.sma(c, 50, i), v4.sma(c, 200, i), v4.atr(b, 14, i)
    if not (c[i] > s50 > s200) or not a:
        return None
    bar = b[i]
    vavg50 = sum(x["v"] for x in b[i - 50:i]) / 50
    for n in (30, 20, 15):
        hi, lo = max(x["h"] for x in b[i - n:i]), min(x["l"] for x in b[i - n:i])
        if (hi - lo) / lo < BASE_MAX_WIDTH and c[i] > hi and bar["v"] > VOL_MULT * vavg50:
            stop = (hi + lo) / 2
            return ("breakout", stop) if c[i] - stop <= v4.MAX_STOP_ATR * a else None
    return None


def apply():
    v4.NAMES = NAMES
    v4.ETFS = ETFS
    v4.RS_TOP = 20
    v4.MAX_POS = 8
    v4.CAP = 0.125
    v4.PER_THEME = 3
    v4.entry_signal = entry_signal


apply()
MAX_NEW = 3
