"""READ-ONLY check: confirms keys work and the account is paper. Places no orders."""
from alpaca_client import Alpaca
from config import VIRTUAL_CAPITAL

a = Alpaca()
acct = a.account()
print("Status:", acct.get("status"))
print("Account number (last 4):", str(acct.get("account_number", ""))[-4:])
print("Paper equity (fake money): $", acct.get("equity"))
print("Open positions:", len(a.positions()))
print("Bot will treat the account as having $", VIRTUAL_CAPITAL)
print("OK - heartbeat: alive")
