# -*- coding: utf-8 -*-
"""Utility to print bid/ask for a Polymarket market."""

import os
from typing import Optional

from get_recent_markets import fetch_latest

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

HOST = "https://clob.polymarket.com"


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


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} MARKET_ID")

    print_bid_ask(sys.argv[1])
