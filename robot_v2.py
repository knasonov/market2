"""Market making robot with hedging (version 2)."""

from __future__ import annotations

import sys
import time
import logging
from typing import Any, Dict, List, Set

from trading_helpers import (
    buy_no,
    sell_no,
    buy_yes,
    cancel_all_orders,
    get_bid_ask_spread,
    get_open_orders,
    get_token_outcomes,
    get_positions,
    get_recent_trades,
)
from telegram1 import send_telegram_message

logging.basicConfig(
    level=logging.INFO,
    filename="robot_v1_log.txt",
    format="%(message)s",
    filemode="a",
)


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
    action = "Sold" if side == "BUY" else "Bought"

    size = trade.get("size")
    try:
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


def hedge_once(market: str) -> None:
    """Balance Yes/No holdings.

    If a BUY order for the needed outcome is already open, hedging is skipped.
    """
    cycle_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    positions = get_positions(market)
    yes_pos = float(positions.get("yes", 0.0))
    no_pos = float(positions.get("no", 0.0))
    logging.info(
        f"[{cycle_ts}] [hedge] Positions – Yes: {yes_pos:.2f}, No: {no_pos:.2f}"
    )

    if abs(yes_pos - no_pos) < 0.0001:
        logging.info(f"[{cycle_ts}] [hedge] Portfolio already balanced")
        return

    spread = get_bid_ask_spread(market)
    yes_ask = spread.get("yes", {}).get("ask")
    no_ask = spread.get("no", {}).get("ask")

    open_orders = get_open_orders(market)
    token_lookup = get_token_outcomes(market)

    def _has_buy_order(outcome: str) -> bool:
        """Return ``True`` if a BUY order for *outcome* is already open."""
        for order in open_orders:
            if str(order.get("side", "")).upper() != "BUY":
                continue
            token_id = order.get("tokenId") or order.get("token_id")
            if token_id is not None and token_lookup.get(str(token_id)) == outcome:
                return True
            if str(order.get("outcome", "")).lower() == outcome:
                return True
        return False

    if open_orders:
        for o in open_orders:
            logging.info(
                f"[{cycle_ts}] [hedge] Open order detail: "
                f"side={o.get('side')}, price={o.get('price')}, "
                f"size={o.get('size')}, token={o.get('tokenId') or o.get('token_id')}"
            )
    else:
        logging.info(f"[{cycle_ts}] [hedge] No open orders")

    if yes_pos > no_pos and yes_ask is not None and no_ask is not None:
        diff = yes_pos - no_pos
        target_price = round(1 - yes_ask, 2)
        delta_cents = int(round((no_ask - target_price) * 100))
        logging.info(
            f"[{cycle_ts}] [hedge] Need {diff:.2f} more 'No' at {target_price:.2f} (delta {delta_cents}c)"
        )
        already_open = _has_buy_order("no")
        if already_open:
            logging.info(f"[{cycle_ts}] [hedge] Existing 'No' buy order found – skipping")
        else:
            logging.info(
                f"[{cycle_ts}] [hedge] Placing buy_no order for {diff:.2f} at delta {delta_cents}c"
            )
            resp = buy_no(market, x_cents_below_ask=delta_cents, size=diff)
            logging.info(f"[{cycle_ts}] [hedge] Order response: {resp}")
    elif no_pos > yes_pos and yes_ask is not None and no_ask is not None:
        diff = no_pos - yes_pos
        target_price = round(1 - no_ask, 2)
        delta_cents = int(round((yes_ask - target_price) * 100))
        logging.info(
            f"[{cycle_ts}] [hedge] Need {diff:.2f} more 'Yes' at {target_price:.2f} (delta {delta_cents}c)"
        )
        already_open = _has_buy_order("yes")
        if already_open:
            logging.info(f"[{cycle_ts}] [hedge] Existing 'Yes' buy order found – skipping")
        else:
            logging.info(
                f"[{cycle_ts}] [hedge] Placing buy_yes order for {diff:.2f} at delta {delta_cents}c"
            )
            resp = buy_yes(market, x_cents_below_ask=delta_cents, size=diff)
            logging.info(f"[{cycle_ts}] [hedge] Order response: {resp}")
    else:
        logging.info(f"[{cycle_ts}] [hedge] Order book data missing – cannot hedge now")


def run_robot(market: str, t_work: int, *, volume: float = 100.0, min_amount: float = 5.0) -> None:
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
            if no_pos < volume:
                buy_size = volume - no_pos
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

            # Attempt to hedge positions every cycle
            hedge_once(market)

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

def batch1():
    if len(sys.argv) < 4:
        sys.exit(
            f"Usage: {sys.argv[0]} MARKET_ID WORK_TIME_SECONDS VOLUME [MIN_AMOUNT]"
        )

    volume = float(sys.argv[3])
    min_amt = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
    run_robot(sys.argv[1], int(sys.argv[2]), volume=volume, min_amount=min_amt)



if __name__ == "__main__":
    batch1()  # Replace with actual market ID for testing