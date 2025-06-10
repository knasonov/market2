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
            balance = float(resp.get("balance", 0))
        positions[outcome] = balance
    return positions


def get_open_orders(market: str) -> List[Dict[str, Any]]:
    """Return open orders for *market*."""
    client = _auth_client()
    condition_id = _resolve_market_id(market)
    return client.get_orders(OpenOrderParams(market=condition_id))


def get_recent_trades(market: str, minutes: int) -> List[Dict[str, Any]]:
    """Return executed trades for *market* in the last *minutes* minutes."""
    client = _auth_client()
    condition_id = _resolve_market_id(market)
    after_ts = int(time.time()) - minutes * 60
    return client.get_trades(TradeParams(market=condition_id, after=after_ts))


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


def sell_no(market: str, x_cents_above_bid: int, *, size: float | None = None) -> Dict[str, Any]:
    """Place a sell order using :func:`market_prices.sellNo`."""
    return _sell_no(market=market, x_cents_above_bid=x_cents_above_bid, size=size)


def cancel_all_orders() -> Dict[str, Any]:
    """Cancel all open orders using :func:`market_prices.cancel_all_orders`."""
    return _cancel_all()

#pos = get_open_orders("0xc3ede0572bba2901df68aac861e1be5a2de742060237d8cf85085e596d210eff")
pos = get_positions("0xc3ede0572bba2901df68aac861e1be5a2de742060237d8cf85085e596d210eff")
print(pos)