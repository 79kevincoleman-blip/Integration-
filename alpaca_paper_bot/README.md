# Alpaca Paper Bot

Self-contained swing-trading bot on an **Alpaca paper account** ($100k virtual, account …6GSX).
No real money. Started 2026-11-12 (as a Webull-priced paper book), moved to Alpaca 2026-11-18.

## Layout
| Path | Purpose |
|---|---|
| `RULES.md` | The strategy: risk, setups, exits, approval mode, pass/fail, schedule |
| `CLAUDE.md` | Project memory: state, decisions, how to resume |
| `bot/paper.py` | Sizing, fill/exit math, scorecard (pure functions) |
| `bot/bridge.py` | Talks to Alpaca **paper** API (URL hard-coded) |
| `bridge_request.json` | Requests for the bridge (push it to run) |
| `backtest/backtest.py` | Backtest of RULES.md on daily bars |
| `backtest/request.json` | Push to rerun the backtest |
| `book/ledger.json` | Positions, orders, cash, history |
| `book/journal.csv` | Every decision with the reason |
| `book/lessons.md` | Daily lessons |
| `tests/` | `python -m pytest alpaca_paper_bot/tests` |

## How it runs (automated)
1. Scheduled Claude tasks (weekdays ET): 08:17 scan + orders, 12:47 sync, 15:47 recap.
2. Claude writes `bridge_request.json`, commits, pushes.
3. GitHub Actions (`.github/workflows/alpaca-bridge.yml`) runs `bot/bridge.py` with repo secrets
   `ALPACA_KEY_ID` + `ALPACA_SECRET_KEY` (or `ALPACA_SECRET`), prints `RESULT` lines.
4. Claude reads the job log, updates `book/`, commits, sends a push notification if anything happened.

Keys live only in GitHub secrets. Nothing in this folder contains a key.

## Not automated
- Real-money (Webull) trades: never automatic; owner confirms each in the Webull app, and only after pass/fail.
- The schedule lives in one Claude session; if that session is archived, re-create the three tasks from CLAUDE.md.
