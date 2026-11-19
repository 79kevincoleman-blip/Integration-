"""Turn Webull order-history JSON (get_order_history output) into webull-journal.csv rows.
Usage: python journal_from_fills.py orders.json >> webull-journal.csv
Stops/targets/R come from the GO sheet of the pre-trade check; fill them in by order id."""
import csv, json, sys
from datetime import datetime


def rows(orders):
    for combo in orders:
        for o in combo["orders"]:
            if o["status"] != "FILLED":
                continue
            fee = sum(float(f["actual_value"]) for f in o.get("fees", []))
            yield {"date": o["filled_time_at"][:10], "type": "TRADE", "ticker": o["symbol"],
                   "side": o["side"], "qty": o["filled_quantity"], "price": o["filled_price"],
                   "stop": "", "target": "", "risk_usd": "", "fees": f"{fee:.2f}",
                   "pnl_usd": "", "r_multiple": "", "note": f"webull order {o['order_id']}"}


FIELDS = ["date", "type", "ticker", "side", "qty", "price", "stop", "target",
          "risk_usd", "fees", "pnl_usd", "r_multiple", "note"]

if __name__ == "__main__":
    w = csv.DictWriter(sys.stdout, FIELDS)
    for r in rows(json.load(open(sys.argv[1]))):
        w.writerow(r)
