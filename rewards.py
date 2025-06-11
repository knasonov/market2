"""Estimate maker reward per share for a market."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from py_clob_client.clob_types import OpenOrderParams
from py_clob_client.order_builder.constants import BUY, SELL

from typing import cast

from market_prices import _auth_client, _resolve_market_id


# Approximate total effective depth used for normalisation.  Markets
# typically have 70k–150k effective shares inside the incentive window.
_TOTAL_EFFECTIVE_DEPTH = Decimal("80000")


def _get_order_book(client, token_id: str):
    """Return order book for ``token_id`` with debug logging."""
    book = client.get_order_book(token_id)
    print(
        f"_get_order_book: token={token_id} "
        f"bids={len(book.bids)} asks={len(book.asks)}"
    )
    return book


def _fetch_mid_prices(client, tokens: List[Dict[str, str]]) -> Dict[str, float]:
    """Return mid price for each ``token_id`` in ``tokens``."""
    prices: Dict[str, float] = {}
    for token in tokens:
        token_id = token.get("token_id")
        if token_id is None:
            continue
        book = _get_order_book(client, token_id)
        if book.bids and book.asks:
            best_bid = Decimal(str(book.bids[-1].price))
            best_ask = Decimal(str(book.asks[-1].price))
            mid_price = (best_bid + best_ask) / 2
            prices[token_id] = float(mid_price)
            print(
                f"_fetch_mid_prices: token={token_id} "
                f"best_bid={best_bid} best_ask={best_ask} mid={mid_price}"
            )
        else:
            print(
                f"_fetch_mid_prices: token={token_id} "
                f"bids={len(book.bids)} asks={len(book.asks)}"
            )
    return prices


def calculate_reward_per_share(market_id: str) -> float:
    """Return an estimated daily reward in USDC per share for *market_id*.

    The function uses the maker incentive formula published by
    Polymarket.  It considers the authenticated user's current open
    orders and assumes total effective depth of roughly 80k shares.
    The result is only a rough approximation.
    """

    client = _auth_client()
    condition_id = _resolve_market_id(market_id)
    market = cast(Dict[str, Any], client.get_market(condition_id))
    print(f"calculate_reward_per_share: condition_id={condition_id}")

    rewards = market.get("rewards", {})
    daily_pool = Decimal("0")
    for rate in rewards.get("rates", []):
        daily_pool += Decimal(str(rate.get("rewards_daily_rate", 0)))
    max_spread = Decimal(str(rewards.get("max_spread", 3)))  # cents
    promo_multiplier = Decimal("1")
    print(f"rewards={rewards}")
    print(f"daily_pool={daily_pool} max_spread={max_spread} promo_multiplier={promo_multiplier}")

    tokens = market.get("tokens", [])
    token_lookup = {t.get("token_id"): t.get("outcome", "").lower() for t in tokens}
    print(f"tokens={tokens}")
    mid_prices = _fetch_mid_prices(client, tokens)
    print(f"mid_prices={mid_prices}")

    orders = client.get_orders(OpenOrderParams(market=condition_id))
    for o in orders:
        if o.get("size") is None and o.get("remainingSize") is not None:
            o["size"] = o.get("remainingSize")
        if o.get("size") is not None:
            o["size"] = float(o["size"]) / 1_000_000
    print(f"orders={orders}")

    q_one = Decimal("0")
    q_two = Decimal("0")
    total_size = Decimal("0")

    for order in orders:
        size = order.get("size")
        price = order.get("price")
        token_id = order.get("tokenId") or order.get("token_id")
        side = order.get("side")
        if size is None or price is None or token_id not in mid_prices:
            continue
        size = Decimal(str(size))
        price = Decimal(str(price))
        mid = Decimal(str(mid_prices[token_id]))
        distance = abs(price - mid) * 100  # convert to cents
        if distance >= max_spread:
            continue
        score = promo_multiplier * ((max_spread - distance) / max_spread) ** 2 * size
        outcome = token_lookup.get(token_id)
        print(
            f"order token={token_id} side={side} size={size} price={price} mid={mid} "
            f"distance={distance} score={score} outcome={outcome}"
        )
        if outcome == "yes" and side == BUY:
            q_one += score
        elif outcome == "no" and side == SELL:
            q_one += score
        elif outcome == "no" and side == BUY:
            q_two += score
        elif outcome == "yes" and side == SELL:
            q_two += score
        total_size += size

    print(f"q_one={q_one} q_two={q_two} total_size={total_size}")
    if q_one == 0 and q_two == 0:
        print("Both q_one and q_two are zero; returning 0.0")
        return 0.0

    yes_token_id = next((tid for tid, out in token_lookup.items() if out == "yes"), None)
    mid_yes = Decimal(str(mid_prices.get(yes_token_id or "", 0.5)))
    print(f"yes_token_id={yes_token_id} mid_yes={mid_yes}")

    if Decimal("0.10") <= mid_yes <= Decimal("0.90"):
        q_min = max(min(q_one, q_two), max(q_one, q_two) / 3)
    else:
        q_min = min(q_one, q_two)
    print(f"q_min={q_min}")

    share = q_min / _TOTAL_EFFECTIVE_DEPTH
    daily_reward = share * daily_pool
    print(f"share={share} daily_reward={daily_reward}")

    if total_size == 0:
        result = float(daily_reward)
        print(f"returning {result} (no open order size)")
        return result
    result = float(daily_reward / total_size)
    print(f"returning {result}")
    return result


calculate_reward_per_share("0x26ed2c7b22d8bbf6789e76bdcd88c22b605df53e88c7b57fb3dc48b7ab259a8f")