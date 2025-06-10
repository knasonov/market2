# -*- coding: utf-8 -*-
"""Utility to print bid/ask for a Polymarket market."""

import os
from typing import Optional, Dict, Any

from get_recent_markets import fetch_latest

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

HOST = "https://clob.polymarket.com"

import time
from decimal import Decimal
from typing import Dict, Any, Optional

def buyNo(
    market: str,
    x_cents_below_ask: int,
    cancel_after_secs: int,
    *,
    size: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Place a limit-buy on the “No” outcome of *market* at (ask − x_cents_below_ask)
    and cancel it after *cancel_after_secs* seconds.

    Parameters
    ----------
    market : str
        Market slug, numeric ID, or full condition ID.
    x_cents_below_ask : int
        How many cents below the current best ask to quote (e.g. 2 → 0.02 USDC).
    cancel_after_secs : int
        Seconds to wait before cancelling the order if it is still open.
    size : float, optional
        Number of shares to buy.  If omitted the market’s minimum size is used.

    Returns
    -------
    Dict[str, Any]
        {
            "placed":  response from POST /order,
            "cancel":  response from DELETE /order  (or None if already filled)
        }
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

    order_id = placed_resp.get("orderId")
    if not order_id:
        # placement failed – nothing to cancel
        return {"placed": placed_resp, "cancel": None}

    # --- wait y seconds then attempt cancel -----------------------------------
    time.sleep(cancel_after_secs*1000)

    try:
        cancel_resp = client.cancel(order_id=order_id)
    except Exception as exc:  # already filled or cancel failed
        cancel_resp = {"error": str(exc)}

    return {"placed": placed_resp, "cancel": cancel_resp}





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
    
    placed, canceled = buyNo(
        market=current_market,
        x_cents_below_ask=1,
        cancel_after_secs=100,
        size=100.0,
    )



    print("Placed order:", placed)
    print("Cancel response:", canceled)

