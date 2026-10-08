# Project B: Alpaca Paper Bot (FAKE $5,000, fully automated)

Authority: full, but only inside risk-rules.md. Paper account only.
- Paper API base URL ONLY: https://paper-api.alpaca.markets. The code must refuse to start if the base URL is anything else.
- Keys live in environment variables / secrets (ALPACA_KEY_ID, ALPACA_SECRET). Never in chat, never in these files.
- Own files only: risk-rules.md, journal.csv, weekly-lessons.md. No Webull data or credentials here.
- Daily heartbeat: bot logs "alive" every run; if no heartbeat by 9:45 AM ET the user is notified.
- Lessons can be COPIED by the user into Webull project; nothing flows back automatically.
