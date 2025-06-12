"""Simple market making robot (version 1).

This script maintains orders on a single Polymarket market using helper
functions from ``trading_helpers``.  The robot keeps up to ``max_amount``
of "No" shares.  If the position is below this target it bids one cent
below the best ask for the difference.  When holding any "No" tokens it
offers them one cent above the best bid.

Orders smaller than ``min_amount`` are skipped to avoid tiny trades.

The order book is checked every minute.  If the working orders are no
longer best bid/ask, all orders are cancelled and new ones are placed.
"""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, List, Set
import logging

logging.basicConfig(
    level=logging.INFO,
    filename="robot_v1_log.txt",
    format="%(message)s",
    filemode="a",
)

from trading_helpers import (
    buy_no,
    sell_no,
    cancel_all_orders,
    get_bid_ask_spread,
    get_open_orders,
    get_positions,
    get_recent_trades,
)
from telegram1 import send_telegram_message


def _has_order(orders: List[Dict[str, Any]], side: str, price: float) -> bool:
    """Return ``True`` if an order with ``side`` and ``price`` exists."""

    side = side.upper()
    target = round(price, 2)
    for order in orders:
        try:
            o_side = str(order.get("side", "")).upper()
            o_price = float(order.get("price"))
        except Exception:
            continue

        if o_side == side and round(o_price, 2) == target:
            return True

    return False


def _summarise_trade(trade: Dict[str, object]) -> str:
    """Return a short summary like ``"Bought 100 No at 91c"``."""

    side = str(trade.get("side", "")).upper()
    # The trade side returned by the API is opposite of our action
    # when trading "No" tokens.
    action = "Sold" if side == "BUY" else "Bought"

    size = trade.get("size")
    try:
        # ``get_recent_trades`` already converts size to token units
        size = float(size) if size is not None else 0.0
    except Exception:
        size = 0.0

    price = trade.get("price")
    try:
        price = float(price) if price is not None else 0.0
    except Exception:
        price = 0.0

    price_cents = round(price * 100)
    return f"{action} {size:.0f} No at {price_cents}c"


def run_robot(market: str, t_work: int, *, max_amount: float = 40.0, min_amount) -> None:
    """Run the maker bot on ``market`` for ``t_work`` seconds."""
    end_ts = time.time() + t_work
    seen_ids: Set[str] = set()

    while time.time() < end_ts:
        cycle_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        logging.info(f"[{cycle_ts}] --- New cycle ---")
        try:
            positions = get_positions(market)
            no_pos = float(positions.get("no", 0.0))
            logging.info(f"[{cycle_ts}] Current 'No' position: {no_pos:.2f} shares")

            spread_info = get_bid_ask_spread(market).get("no", {})
            best_bid = spread_info.get("bid")
            best_ask = spread_info.get("ask")
            if best_bid is None or best_ask is None:
                logging.info(f"[{cycle_ts}] Order book empty, sleeping")
                time.sleep(60)
                continue

            logging.info(
                f"[{cycle_ts}] Best bid: {best_bid}, best ask: {best_ask}"
            )

            distance_cents = 1
            if best_ask - best_bid > 0.01:
                spread_cents = round((best_ask - best_bid) * 100)
                distance_cents = int(spread_cents / 2 + 1)
            distance = distance_cents / 100

            buy_price = round(best_ask - distance, 2)
            sell_price = round(best_bid + distance, 2)
            logging.info(
                f"[{cycle_ts}] Target buy price: {buy_price}, target sell price: {sell_price}"
            )

            desired: List[tuple[str, float, float]] = []
            if no_pos < max_amount:
                buy_size = max_amount - no_pos
                if buy_size >= min_amount:
                    desired.append(("BUY", buy_price, buy_size))
                else:
                    logging.info(
                        f"[{cycle_ts}] Buy size {buy_size:.2f} below minimum"
                    )
            if no_pos > 0:
                sell_size = no_pos
                if sell_size >= min_amount:
                    desired.append(("SELL", sell_price, sell_size))
                else:
                    logging.info(
                        f"[{cycle_ts}] Sell size {sell_size:.2f} below minimum"
                    )

            open_orders = get_open_orders(market)
            if open_orders:
                for o in open_orders:
                    logging.info(
                        f"[{cycle_ts}] Open order detail: "
                        f"side={o.get('side')}, price={o.get('price')}, "
                        f"size={o.get('size')}, token={o.get('tokenId') or o.get('token_id')}"
                    )
            else:
                logging.info(f"[{cycle_ts}] No open orders")

            prices_ok = True
            for s, p, _ in desired:
                found = _has_order(open_orders, s, p)
                logging.info(
                    f"[{cycle_ts}] Looking for {s} order at {p:.2f} -> {'found' if found else 'missing'}"
                )
                prices_ok = prices_ok and found

            if not prices_ok:
                logging.info(f"[{cycle_ts}] Orders not at desired prices – replacing")
                cancel_resp = cancel_all_orders()
                logging.info(f"[{cycle_ts}] cancel_all_orders() -> {cancel_resp}")
                for side, price, size in desired:
                    logging.info(
                        f"[{cycle_ts}] Placing {side} order for {size:.2f} shares at {price}"
                    )
                    if side == "BUY":
                        resp = buy_no(
                            market=market, x_cents_below_ask=distance_cents, size=size
                        )
                    else:
                        resp = sell_no(
                            market=market, x_cents_above_bid=distance_cents, size=size
                        )
                    logging.info(f"[{cycle_ts}] Order response: {resp}")
            else:
                logging.info(f"[{cycle_ts}] Orders already at best prices")

            # Check for newly filled orders and alert via Telegram
            trades = get_recent_trades(market, 2)
            for trade in trades:
                trade_id = str(trade.get("id"))
                if trade_id not in seen_ids:
                    msg = _summarise_trade(trade)
                    send_telegram_message(msg)
                    seen_ids.add(trade_id)

        except Exception as exc:
            logging.exception(f"[{cycle_ts}] Error during cycle: {exc}")

        time.sleep(60)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(
            f"Usage: {sys.argv[0]} MARKET_ID WORK_TIME_SECONDS [MIN_AMOUNT]"
        )

    min_amt = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
    run_robot(sys.argv[1], int(sys.argv[2]), min_amount=min_amt)
