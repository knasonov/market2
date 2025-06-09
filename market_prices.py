# -*- coding: utf-8 -*-
"""Utility to print bid/ask for a Polymarket market."""

import os
from typing import Optional

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


def print_bid_ask(market_id: str) -> None:
    """Fetch market and print best bid and ask for each outcome."""
    client = _auth_client()
    market = client.get_market(market_id)

    for token in market.get("tokens", []):
        token_id = token.get("token_id")
        outcome = token.get("outcome", "")
        book = client.get_order_book(token_id)
        best_bid: Optional[str] = book.bids[0].price if book.bids else None
        best_ask: Optional[str] = book.asks[0].price if book.asks else None
        print(f"Outcome '{outcome}': bid={best_bid}, ask={best_ask}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} MARKET_ID")

    print_bid_ask(sys.argv[1])
