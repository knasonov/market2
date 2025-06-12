"""Helper functions for portfolio and order management."""
from __future__ import annotations

import time
from typing import Any, Dict, List
from py_clob_client.clob_types import AssetType

from py_clob_client.client import (
    BalanceAllowanceParams,
    OpenOrderParams,
    TradeParams,
)

from market_prices import (
    _auth_client,
    _resolve_market_id,
    buyNo as _buy_no,
    sellNo as _sell_no,
    buyYes as _buy_yes,
    cancel_all_orders as _cancel_all,
)


def get_positions(market: str) -> Dict[str, float]:
    """Return current token balances for the given market."""
    client = _auth_client()
    condition_id = _resolve_market_id(market)
    market_info = client.get_market(condition_id)

    positions: Dict[str, float] = {}
    for token in market_info.get("tokens", []):
        token_id = token.get("token_id")
        outcome = token.get("outcome", "").lower()
        resp = client.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=token_id))
        balance = 0.0
        if isinstance(resp, dict):
            balance = float(resp.get("balance", 0)) / 1_000_000
        positions[outcome] = balance
    return positions


def get_token_outcomes(market: str) -> Dict[str, str]:
    """Return mapping from token ID to outcome name for ``market``."""
    client = _auth_client()
    condition_id = _resolve_market_id(market)
    market_info = client.get_market(condition_id)

    outcomes: Dict[str, str] = {}
    for token in market_info.get("tokens", []):
        token_id = token.get("token_id")
        outcome = token.get("outcome", "").lower()
        if token_id is not None:
            outcomes[str(token_id)] = outcome
    return outcomes


def get_open_orders(market: str) -> List[Dict[str, Any]]:
    """Return open orders for *market* with a valid ``size`` field."""
    client = _auth_client()
    condition_id = _resolve_market_id(market)
    orders = client.get_orders(OpenOrderParams(market=condition_id))

    # Some library versions return the open amount under different keys. Normalise
    # to always expose ``size`` in token units.
    for o in orders:
        if o.get("size") is None:
            if o.get("remainingSize") is not None:
                o["size"] = o.get("remainingSize")
            elif o.get("sizeRemaining") is not None:
                o["size"] = o.get("sizeRemaining")
            elif o.get("remaining_amount") is not None:
                o["size"] = o.get("remaining_amount")
        if o.get("size") is not None:
            try:
                o["size"] = float(o["size"]) / 1_000_000
            except Exception:
                pass
    return orders


def get_recent_trades(market: str, minutes: int) -> List[Dict[str, Any]]:
    """Return executed trades for *market* in the last *minutes* minutes."""
    client = _auth_client()
    condition_id = _resolve_market_id(market)
    after_ts = int(time.time()) - minutes * 60
    trades = client.get_trades(TradeParams(market=condition_id, after=after_ts))
    for t in trades:
        if t.get("size") is not None:
            t["size"] = float(t["size"]) / 1_000_000
    return trades


def get_bid_ask_spread(market: str) -> Dict[str, Dict[str, float]]:
    """Return best bid, best ask and spread for each outcome of *market*."""
    client = _auth_client()
    condition_id = _resolve_market_id(market)
    market_info = client.get_market(condition_id)

    info: Dict[str, Dict[str, float]] = {}
    for token in market_info.get("tokens", []):
        token_id = token.get("token_id")
        outcome = token.get("outcome", "").lower()
        book = client.get_order_book(token_id)
        bid = float(book.bids[-1].price) if book.bids else None
        ask = float(book.asks[-1].price) if book.asks else None
        spread = None
        if bid is not None and ask is not None:
            spread = ask - bid
        info[outcome] = {"bid": bid, "ask": ask, "spread": spread}
    return info


def buy_no(market: str, x_cents_below_ask: int, *, size: float | None = None) -> Dict[str, Any]:
    """Place a buy order using :func:`market_prices.buyNo`."""
    return _buy_no(market=market, x_cents_below_ask=x_cents_below_ask, size=size)


def buy_yes(market: str, x_cents_below_ask: int, *, size: float | None = None) -> Dict[str, Any]:
    """Place a buy order using :func:`market_prices.buyYes`."""
    return _buy_yes(market=market, x_cents_below_ask=x_cents_below_ask, size=size)


def sell_no(market: str, x_cents_above_bid: int, *, size: float | None = None) -> Dict[str, Any]:
    """Place a sell order using :func:`market_prices.sellNo`."""
    return _sell_no(market=market, x_cents_above_bid=x_cents_above_bid, size=size)


def cancel_all_orders() -> Dict[str, Any]:
    """Cancel all open orders using :func:`market_prices.cancel_all_orders`."""
    return _cancel_all()
