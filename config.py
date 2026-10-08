"""Settings for the Alpaca PAPER bot. Keys come from environment variables only."""
import os

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
DATA_BASE_URL = "https://data.alpaca.markets"

# The Alpaca paper account usually starts with ~$100,000 of fake money.
# The bot pretends it only has this much, so sizing matches the $5,000 plan.
VIRTUAL_CAPITAL = 5000.0

# Risk rules (mirror risk-rules.md)
NORMAL_POSITION_PCT = 0.15
MAX_DIP_POSITION_PCT = 0.30
MAX_POSITIONS = 8
MIN_CASH_PCT = 0.10
MAX_RISK_PER_TRADE_PCT = 0.02
PAUSE_DRAWDOWN_PCT = 0.30


def get_keys():
    key = os.environ.get("ALPACA_KEY_ID")
    secret = os.environ.get("ALPACA_SECRET")
    if not key or not secret:
        raise SystemExit("Missing ALPACA_KEY_ID / ALPACA_SECRET environment variables.")
    return key, secret


def get_base_url():
    url = os.environ.get("ALPACA_BASE_URL", PAPER_BASE_URL).rstrip("/")
    if url != PAPER_BASE_URL:
        raise SystemExit(f"REFUSING TO RUN: base URL must be the PAPER url, got {url}")
    return url
