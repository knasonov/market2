"""Estimate maker reward per share for a market."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Tuple

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


def _get_top_levels(client, token_id: str, depth: int = 3) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
    """Return ``depth`` best bids and asks for ``token_id``.

    Each entry is ``(price, size)`` as :class:`~decimal.Decimal` objects.  The
    order book returned by the API lists prices from worst to best, so the
    final entries represent the best orders.
    """
    book = _get_order_book(client, token_id)
    best_bids = []
    best_asks = []

    for b in reversed(book.bids[-depth:]):
        try:
            price = Decimal(str(b.price))
            size = Decimal(str(b.size))
        except Exception:
            continue
        best_bids.append((price, size))

    # ``book.asks`` is also sorted from worst to best, so reverse the slice to
    # return prices from best to worst just like bids.
    for a in reversed(book.asks[-depth:]):
        try:
            price = Decimal(str(a.price))
            size = Decimal(str(a.size))
        except Exception:
            continue
        best_asks.append((price, size))

    print(
        f"_get_top_levels: token={token_id} "
        f"bids={[str(p) for p, _ in best_bids]} "
        f"asks={[str(p) for p, _ in best_asks]}"
    )

    print(f"best bids:{best_bids}")
    print(f"best asks:{best_asks}")
    return best_bids, best_asks


def _fetch_mid_prices(client, tokens: List[Dict[str, str]]) -> Dict[str, float]:
    """Return mid price for each ``token_id`` in ``tokens``.

    This uses :func:`_get_top_levels` to examine the best bid and ask for each
    token.  If either side of the book is empty the token is skipped.
    """
    prices: Dict[str, float] = {}
    for token in tokens:
        token_id = token.get("token_id")
        if token_id is None:
            continue
        bids, asks = _get_top_levels(client, token_id, depth=3)
        if not bids or not asks:
            print(
                f"_fetch_mid_prices: token={token_id} "
                f"bids={len(bids)} asks={len(asks)}"
            )
            continue

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2
        prices[token_id] = float(mid_price)
        print(
            f"_fetch_mid_prices: token={token_id} "
            f"best_bid={best_bid} best_ask={best_ask} mid={mid_price}"
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



def calculate_simple_rewards(market_id: str) -> Dict[str, Dict[str, float | None]]:
    """Return rough reward/share estimates using top-of-book depth.

    The function fetches the three best bids and asks for each outcome and
    computes an "effective" size using the simplified formula::

        eff_size = lvl1 + lvl2 / 4 + lvl3 / 9

    Rewards per share are then approximated as ``daily_pool * 100 / eff_size``.
    The return value maps each outcome ("yes", "no", etc.) to a dictionary with
    ``reward_per_share_bid`` and ``reward_per_share_ask`` fields.  If either side
    of the book is empty ``None`` is returned for that value.
    """

    client = _auth_client()
    condition_id = _resolve_market_id(market_id)
    market = cast(Dict[str, Any], client.get_market(condition_id))

    rewards = market.get("rewards", {})
    daily_pool = Decimal("0")
    for rate in rewards.get("rates", []):
        daily_pool += Decimal(str(rate.get("rewards_daily_rate", 0)))

    tokens = market.get("tokens", [])
    result: Dict[str, Dict[str, float | None]] = {}

    for token in tokens:
        token_id = token.get("token_id")
        outcome = token.get("outcome", "").lower()
        if token_id is None:
            continue

        bids, asks = _get_top_levels(client, token_id, depth=3)

        def _effective_size(levels: List[Tuple[Decimal, Decimal]]) -> Decimal:
            size = Decimal("0")
            if len(levels) > 0:
                size += levels[0][1]
            if len(levels) > 1:
                size += levels[1][1] / Decimal("4")
            if len(levels) > 2:
                size += levels[2][1] / Decimal("9")
            return size
        
        
        eff_bid = _effective_size(bids)
        print(f"Effective size for bids: {eff_bid}")
        eff_ask = _effective_size(asks)
        print(f"Effective size for asks: {eff_ask}")
        print("daily pool:", daily_pool)

        bid_rps: float | None = None
        ask_rps: float | None = None

        if eff_bid > 0:
            bid_rps = float((daily_pool * Decimal("100")) / eff_bid)
        if eff_ask > 0:
            ask_rps = float((daily_pool * Decimal("100")) / eff_ask)

        result[outcome] = {
            "reward_per_share_bid": bid_rps,
            "reward_per_share_ask": ask_rps,
        }

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} MARKET_ID")

    print(calculate_simple_rewards(sys.argv[1]))
