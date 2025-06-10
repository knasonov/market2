"""Background service to alert on newly filled trades."""

from __future__ import annotations

import time
from typing import Dict, Set

from market_prices import _auth_client
from telegram1 import send_telegram_message


def _summarise_trade(trade: Dict[str, object]) -> str:
    """Return a short summary like ``"Bought 100 No at 91c"``."""

    side = str(trade.get("side", "")).upper()
    action = "Bought" if side == "BUY" else "Sold"

    size = trade.get("size")
    try:
        size = float(size) / 1_000_000 if size is not None else 0.0
    except Exception:
        size = 0.0

    price = trade.get("price")
    try:
        price = float(price) if price is not None else 0.0
    except Exception:
        price = 0.0

    price_cents = round(price * 100)
    return f"{action} {size:.0f} No at {price_cents}c"


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
                    msg = _summarise_trade(trade)
                    send_telegram_message(msg)
                    seen_ids.add(trade_id)
        except Exception as exc:
            print(f"Error checking trades: {exc}")

        time.sleep(60)


if __name__ == "__main__":
    main()
