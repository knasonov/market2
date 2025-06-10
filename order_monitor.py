"""Background service to alert on newly filled trades."""

from __future__ import annotations

import json
import time
from typing import Set

from market_prices import _auth_client
from telegram1 import send_telegram_message


def main() -> None:
    """Poll the CLOB API every minute and notify on new trades."""

    client = _auth_client()
    seen_ids: Set[str] = set()

    while True:
        try:
            trades = client.get_trades()
            for trade in trades:
                trade_id = str(trade.get("id"))
                if trade_id not in seen_ids:
                    msg = f"Filled trade: {json.dumps(trade)}"
                    send_telegram_message(msg)
                    seen_ids.add(trade_id)
        except Exception as exc:
            print(f"Error checking trades: {exc}")

        time.sleep(60)


if __name__ == "__main__":
    main()
