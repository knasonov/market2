#!/usr/bin/env python3
"""
polymarket_buy.py
-----------------
Login with your Polygon key and buy one share in the newest Polymarket market.

Prerequisites
-------------
    pip install py-clob-client
    (make sure polymarket_dump.py is import-visible)
Environment
-----------
    POLY_PRIVATE_KEY     : *required* – Polygon private key (0x…)
    POLY_FUNDER_ADDRESS  : proxy wallet that holds USDC (optional if trading from EOA)
    POLY_SIGNATURE_TYPE  : 1 (email), 2 (browser wallet), 3 (EOA); default 1
    POLY_CLOB_URL        : CLOB host, defaults to https://clob.polymarket.com
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

# Re-use the fetcher you already wrote
from polymarket_dump import fetch_latest


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

HOST: str = os.getenv("POLY_CLOB_URL", "https://clob.polymarket.com")
CHAIN_ID: int = 137  # Polygon mainnet

try:
    PRIVATE_KEY: str = os.environ["POLY_PRIVATE_KEY"]
except KeyError:
    sys.exit("❌  Set POLY_PRIVATE_KEY in your environment.")

FUNDER_ADDRESS: str | None = os.getenv("POLY_FUNDER_ADDRESS")
SIG_TYPE: int = int(os.getenv("POLY_SIGNATURE_TYPE", "1"))


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def get_client() -> ClobClient:
    """
    Initialise a signed CLOB client and derive (or fetch) API credentials.
    """
    client = ClobClient(
        HOST,
        key=PRIVATE_KEY,
        chain_id=CHAIN_ID,
        signature_type=SIG_TYPE,
        funder=FUNDER_ADDRESS,
    )
    # Derive or fetch L2 API key/secret/passphrase in one call
    client.set_api_creds(client.create_or_derive_api_creds())
    return client


def pick_token_id(market: Dict[str, Any]) -> str:
    """
    Return the first outcome’s ERC-1155 token ID from a market record.
    `clobTokenIds` is stored as a JSON-encoded string – decode it first.
    """
    token_list: List[str] = json.loads(market["clobTokenIds"])
    return token_list[0]


def compute_size(market: Dict[str, Any]) -> float:
    """
    Honour Polymarket’s per-market minimum size.
    """
    minimum: float = float(market.get("orderMinSize", 1))
    return max(1.0, minimum)


def compute_price(market: Dict[str, Any]) -> float:
    """
    Use the current best ask if available; fall back to 1.00 USDC so the order
    is always marketable.
    """
    try:
        best_ask = float(market["bestAsk"])
        if best_ask > 0:
            return best_ask
    except (KeyError, TypeError, ValueError):
        pass
    return 1.00  # worst-case price, still guaranteed to fill


# --------------------------------------------------------------------------- #
# Main routine
# --------------------------------------------------------------------------- #

def buy_one_share_in_latest() -> Dict[str, Any]:
    """
    Fetch the newest market and submit a FOK order for one share
    (or the enforced minimum), priced to fill immediately.
    """
    market = fetch_latest(1)[0]
    token_id = pick_token_id(market)
    size = compute_size(market)
    price = compute_price(market)

    client = get_client()

    order_args = OrderArgs(
        price=price,
        size=size,
        side=BUY,
        token_id=token_id,
    )
    signed = client.create_order(order_args)

    # FOK = “all-or-nothing right now”; if it’s not filled instantly the order is cancelled
    response = client.post_order(signed, OrderType.FOK)
    return response


if __name__ == "__main__":
    result = buy_one_share_in_latest()
    print("✅ Order response:")
    print(result)
