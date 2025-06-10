# -*- coding: utf-8 -*-
"""Utility to print bid/ask for a Polymarket market."""

import os
from typing import Dict, Any, Optional

from get_recent_markets import fetch_latest

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

HOST = "https://clob.polymarket.com"

from decimal import Decimal

def buyNo(
    market: str,
    x_cents_below_ask: int,
    *,
    size: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Place a limit-buy on the “No” outcome of *market* at (ask − x_cents_below_ask).

    Parameters
    ----------
    market : str
        Market slug, numeric ID, or full condition ID.
    x_cents_below_ask : int
        How many cents below the current best ask to quote (e.g. 2 → 0.02 USDC).
    size : float, optional
        Number of shares to buy.  If omitted the market’s minimum size is used.

    Returns
    -------
    Dict[str, Any]
        Response from POST /order.
    """
    # --- initialise client and resolve market ---------------------------------
    client = _auth_client()
    condition_id = _resolve_market_id(market)
    market_info = client.get_market(condition_id)

    # --- find token id for the “No” side --------------------------------------
    no_token_id: Optional[str] = None
    for token in market_info.get("tokens", []):
        if token.get("outcome", "").lower() == "no":
            no_token_id = token.get("token_id")
            break
    if no_token_id is None:
        raise RuntimeError(f"'No' outcome not found for market {market!r}")

    # --- choose order size ----------------------------------------------------
    if size is None:
        size = max(2.0, float(market_info.get("orderMinSize", 1)))

    # --- compute quote price --------------------------------------------------
    book = client.get_order_book(no_token_id)
    if not book.asks:
        raise RuntimeError("No asks to quote against – order book empty.")

    best_ask = Decimal(str(book.asks[-1].price))
    delta = Decimal(x_cents_below_ask) / Decimal("100")
    price = best_ask - delta
    # Tick size is 0.01 USDC – enforce lower bound.
    if price < Decimal("0.01"):
        price = Decimal("0.01")

    # --- place order ----------------------------------------------------------
    order_args = OrderArgs(
        price=float(price),
        size=float(size),
        side=BUY,
        token_id=no_token_id,
    )
    signed = client.create_order(order_args)
    placed_resp = client.post_order(signed, OrderType.GTC)

    return placed_resp


def sellNo(
    market: str,
    x_cents_above_bid: int,
    *,
    size: Optional[float] = None,
) -> Dict[str, Any]:
    """Sell the "No" outcome slightly above the best bid.

    Parameters
    ----------
    market : str
        Market slug, numeric ID, or full condition ID.
    x_cents_above_bid : int
        How many cents above the best bid to quote.
    size : float, optional
        Number of shares to sell; defaults to the market minimum.

    Returns
    -------
    Dict[str, Any]
        Response from POST /order
    """

    client = _auth_client()
    condition_id = _resolve_market_id(market)
    market_info = client.get_market(condition_id)

    # locate the "No" token
    no_token_id: Optional[str] = None
    for token in market_info.get("tokens", []):
        if token.get("outcome", "").lower() == "no":
            no_token_id = token.get("token_id")
            break
    if no_token_id is None:
        raise RuntimeError(f"'No' outcome not found for market {market!r}")

    if size is None:
        size = max(2.0, float(market_info.get("orderMinSize", 1)))

    book = client.get_order_book(no_token_id)
    if not book.bids:
        raise RuntimeError("No bids to quote against – order book empty.")

    best_bid = Decimal(str(book.bids[-1].price))
    delta = Decimal(x_cents_above_bid) / Decimal("100")
    price = best_bid + delta
    if price > Decimal("0.99"):
        price = Decimal("0.99")

    order_args = OrderArgs(
        price=float(price),
        size=float(size),
        side=SELL,
        token_id=no_token_id,
    )
    signed = client.create_order(order_args)
    placed_resp = client.post_order(signed, OrderType.GTC)

    return placed_resp





def _auth_client() -> ClobClient:
    """Return an authenticated ClobClient using env vars like poly_test."""
    try:
        pk = os.environ["POLY_PRIVATE_KEY"]
    except KeyError as exc:
        raise RuntimeError("POLY_PRIVATE_KEY must be set") from exc

    sig_type = int(os.getenv("POLY_SIGNATURE_TYPE", "1"))
    funder = os.getenv("POLY_FUNDER_ADDRESS") or None

    client = ClobClient(
        host=HOST,
        key=pk,
        chain_id=POLYGON,
        signature_type=sig_type,
        funder=funder,
    )
    client.set_api_creds(client.create_or_derive_api_creds())
    return client


def _resolve_market_id(market_id: str, *, search_limit: int = 10000) -> str:
    """Return the condition ID for ``market_id``.

    ``market_id`` may be a full condition ID, a numeric market ID, or a slug.
    The most recent markets are searched when resolution is required.
    """

    if market_id.startswith("0x"):
        return market_id

    markets = fetch_latest(search_limit)
    for market in markets:
        if str(market.get("id")) == str(market_id) or market.get("slug") == market_id:
            if market.get("slug") == market_id:
                print(f"Slug '{market_id}' -> market ID {market.get('id')}")
            return market.get("conditionId")

    raise RuntimeError(
        f"Market {market_id} not found in last {search_limit} markets"
    )

def print_bid_ask(market_id: str) -> None:
    """Fetch market and print best bid and ask for each outcome."""
    client = _auth_client()
    condition_id = _resolve_market_id(market_id)
    market = client.get_market(condition_id)

    for token in market.get("tokens", []):
        token_id = token.get("token_id")
        outcome = token.get("outcome", "")
        book = client.get_order_book(token_id)
        # Bids and asks are sorted worst-to-best so use the last entry
        best_bid: Optional[str] = book.bids[-1].price if book.bids else None
        best_ask: Optional[str] = book.asks[-1].price if book.asks else None
        print(f"Outcome '{outcome}': bid={best_bid}, ask={best_ask}")


def cancel_all_orders() -> Dict[str, Any]:
    """Cancel all open orders for the authenticated user."""
    client = _auth_client()
    try:
        return client.cancel_all()
    except Exception as exc:
        return {"error": str(exc)}


def buy2no(market: str) -> Dict[str, Any]:
    """Buy 1 share of the 'No' outcome of *market* at the current ask price."""

    client = _auth_client()
    condition_id = _resolve_market_id(market)
    market_info = client.get_market(condition_id)

    # Find the token ID for the "No" outcome
    no_token_id: Optional[str] = None
    for token in market_info.get("tokens", []):
        if token.get("outcome", "").lower() == "no":
            no_token_id = token.get("token_id")
            break

    if not no_token_id:
        raise RuntimeError(f"'No' outcome not found for market {market}")

    # Honour market minimum size
    size = max(2.0, float(market_info.get("orderMinSize", 1)))

    # Determine the best ask for the No token
    book = client.get_order_book(no_token_id)
    price = float(book.asks[-1].price) if book.asks else 1.0

    order_args = OrderArgs(
        price=price,
        size=size,
        side=BUY,
        token_id=no_token_id,
    )
    signed = client.create_order(order_args)
    return client.post_order(signed, OrderType.GTC)


if __name__ == "__main__":
    #import sys

    #if len(sys.argv) != 2:
    #    sys.exit(f"Usage: {sys.argv[0]} MARKET_ID")

    #print_bid_ask(sys.argv[1])

    current_market = "0xc3ede0572bba2901df68aac861e1be5a2de742060237d8cf85085e596d210eff"
    
    """
    placed = buyNo(
        market=current_market,
        x_cents_below_ask=1,
        size=100.0,
    )
    """

    #cancel_all_orders()
    """
    sellNo(
        market=current_market,
        x_cents_above_bid=1,
        size=95.0,
    )
    """


