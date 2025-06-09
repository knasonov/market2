#!/usr/bin/env python3
"""
polymarket_dump.py
==================

Fetch the *N* most-recent Polymarket markets and print the raw payload
exactly as the server returns it.

Usage
-----

    python polymarket_dump.py                # default: last 10 markets
    python polymarket_dump.py 25             # last 25 markets
    python polymarket_dump.py --limit 50     # last 50 markets
    python polymarket_dump.py -l 5 --raw     # show raw, unformatted JSON

Environment variables
---------------------
POLYMARKET_API_URL : alternate base URL (defaults to
                     "https://gamma-api.polymarket.com/markets")
REQUESTS_TIMEOUT   : network timeout in seconds (default 10)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

import requests
from requests.exceptions import RequestException

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DEFAULT_API_URL = "https://gamma-api.polymarket.com/markets"
API_URL = os.getenv("POLYMARKET_API_URL", DEFAULT_API_URL)
TIMEOUT = int(os.getenv("REQUESTS_TIMEOUT", "10"))  # seconds


# --------------------------------------------------------------------------- #
# Networking
# --------------------------------------------------------------------------- #

def fetch_latest(limit: int) -> List[Dict[str, Any]]:
    """
    Return *limit* newest markets (order=id DESC) from the Gamma endpoint.
    """
    params: Dict[str, str] = {
        "limit": str(limit),
        "order": "id",
        "ascending": "false",
    }

    response = requests.get(API_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()
    return data["data"] if isinstance(data, dict) else data


def find_market_id_by_slug(slug: str, *, search_limit: int = 100) -> str:
    """Return the numeric market ID that matches *slug*.

    The newest ``search_limit`` markets are fetched using :func:`fetch_latest`.
    The function prints a short message and returns the ID if a match is found.
    ``RuntimeError`` is raised when no market uses the provided slug.
    """

    markets = fetch_latest(search_limit)
    for market in markets:
        if market.get("slug") == slug:
            market_id = str(market.get("id"))
            print(f"Found slug '{slug}' -> market ID {market_id}")
            return market_id

    raise RuntimeError(
        f"Slug '{slug}' not found in last {search_limit} markets"
    )


# --------------------------------------------------------------------------- #
# CLI / main
# --------------------------------------------------------------------------- #

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Dump raw Polymarket market records."
    )
    ap.add_argument(
        "limit",
        nargs="?",
        type=int,
        default=10,
        help="number of newest markets to fetch (default 10)",
    )
    ap.add_argument(
        "-l",
        "--limit",
        dest="limit_flag",
        type=int,
        help="same as positional LIMIT, overrides it if both given",
    )
    ap.add_argument(
        "--raw",
        action="store_true",
        help="output a single compact JSON blob instead of pretty-printing",
    )
    ap.add_argument(
        "--find-id",
        metavar="SLUG",
        help="search the newest markets for SLUG and print the numeric id",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    limit = args.limit_flag if args.limit_flag is not None else args.limit

    if args.find_id:
        try:
            find_market_id_by_slug(args.find_id, search_limit=limit)
        except RequestException as exc:
            sys.exit(f"Request failed: {exc}")
        except RuntimeError as exc:
            sys.exit(str(exc))
        return

    try:
        markets = fetch_latest(limit)
    except RequestException as exc:
        sys.exit(f"Request failed: {exc}")

    if args.raw:
        # Compact single-line JSON for piping or further processing
        json.dump(markets, sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")
        return

    # Pretty print each record with indentation
    for idx, market in enumerate(markets, start=1):
        print(f"\n=== Market {idx}/{len(markets)} ===")
        print(json.dumps(market, indent=2, sort_keys=True))

    print(f"\n✓ Fetched {len(markets)} markets.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)


"""
Sample output structure:
=== Market 10/10 ===
{
  "acceptingOrders": true,
  "acceptingOrdersTimestamp": "2025-06-09T08:01:08Z",
  "active": true,
  "approved": true,
  "archived": false,
  "automaticallyActive": true,
  "bestAsk": 1,
  "clearBookOnStart": true,
  "clobTokenIds": "[\"115093477542595845459769642510663906754645636077470857739371815633441497856930\", \"111033623022233125288447078063536634338953857359981191096322678314504369414568\"]",
  "closed": false,
  "conditionId": "0x5387dec0a07436f792cd86d75cd5d24653f0e3d09690b3849e5bd9067d48de5c",
  "createdAt": "2025-06-09T08:00:33.634894Z",
  "cyom": false,
  "deploying": false,
  "description": "In the upcoming MLB game, scheduled for June 10 at 7:10PM ET:\nIf the Washington Nationals win, the market will resolve to \u201cNationals\u201d.\nIf the New York Mets win, the market will resolve to \u201cMets\u201d.\nIf the game is postponed, this market will remain open until the game has been completed.\nIf the game is canceled entirely, with no make-up game, this market will resolve 50-50.\nTo know when a postponed game will be played, please check the home team's schedule on MLB.com for the listed team and look for the game described as a makeup game.",
  "enableOrderBook": true,
  "endDate": "2025-06-17T23:10:00Z",
  "endDateIso": "2025-06-17",
  "events": [
    {
      "active": true,
      "archived": false,
      "automaticallyActive": true,
      "closed": false,
      "commentCount": 0,
      "createdAt": "2025-06-09T08:00:33.40229Z",
      "creationDate": "2025-06-10T23:10:00Z",
      "cyom": false,
      "deploying": false,
      "description": "In the upcoming MLB game, scheduled for June 10 at 7:10PM ET:\nIf the Washington Nationals win, the market will resolve to \u201cNationals\u201d.\nIf the New York Mets win, the market will resolve to \u201cMets\u201d.\nIf the game is postponed, this market will remain open until the game has been completed.\nIf the game is canceled entirely, with no make-up game, this market will resolve 50-50.\nTo know when a postponed game will be played, please check the home team's schedule on MLB.com for the listed team and look for the game described as a makeup game.",
      "enableNegRisk": false,
      "enableOrderBook": true,
      "endDate": "2025-06-10T23:10:00Z",
      "eventDate": "2025-06-10",
      "eventWeek": 12,
      "featured": false,
      "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/Repetitive-markets/MLB.jpg",
      "id": "26359",
      "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/Repetitive-markets/MLB.jpg",
      "negRisk": false,
      "negRiskAugmented": false,
      "new": false,
      "openInterest": 0,
      "pendingDeployment": false,
      "period": "NS",
      "restricted": true,
      "series": [
        {
          "active": true,
          "archived": false,
          "closed": false,
          "commentCount": 2003,
          "commentsEnabled": false,
          "competitive": "0",
          "createdAt": "2022-10-13T00:37:01.013Z",
          "createdBy": "15",
          "featured": false,
          "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/Repetitive-markets/MLB.jpg",
          "id": "3",
          "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/Repetitive-markets/MLB.jpg",
          "layout": "default",
          "liquidity": 174569.53159,
          "new": false,
          "publishedAt": "2022-10-13 00:37:11.511+00",
          "recurrence": "daily",
          "restricted": true,
          "seriesType": "single",
          "slug": "mlb",
          "startDate": "2021-01-01T17:00:00Z",
          "ticker": "mlb",
          "title": "MLB",
          "updatedAt": "2025-06-09T09:08:24.39418Z",
          "updatedBy": "15",
          "volume": 179054.060267,
          "volume24hr": 0
        }
      ],
      "seriesSlug": "mlb",
      "showAllOutcomes": false,
      "showMarketImages": true,
      "slug": "mlb-wsh-nym-2025-06-10",
      "startDate": "2025-06-09T08:02:22.334142Z",
      "startTime": "2025-06-10T23:10:00Z",
      "ticker": "mlb-wsh-nym-2025-06-10",
      "title": "Nationals vs. Mets",
      "updatedAt": "2025-06-09T09:08:23.303814Z"
    }
  ],
  "fee": "20000000000000000",
  "fpmmLive": true,
  "funded": false,
  "gameStartTime": "2025-06-10 23:10:00+00",
  "groupItemTitle": "Nationals vs. Mets",
  "hasReviewedDates": true,
  "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/Repetitive-markets/MLB.jpg",
  "id": "550834",
  "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/Repetitive-markets/MLB.jpg",
  "manualActivation": false,
  "marketMakerAddress": "",
  "negRisk": false,
  "negRiskOther": false,
  "new": true,
  "notificationsEnabled": false,
  "orderMinSize": 5,
  "orderPriceMinTickSize": 0.01,
  "outcomePrices": "[\"0.5\", \"0.5\"]",
  "outcomes": "[\"Nationals\", \"Mets\"]",
  "pagerDutyNotificationEnabled": false,
  "pendingDeployment": false,
  "question": "Nationals vs. Mets",
  "questionID": "0xfba0131a77471ab27e13bdcbdfeaf3af54c83c19c7e1212e3fb4f9f39b40e491",
  "ready": false,
  "readyForCron": false,
  "resolutionSource": "https://www.mlb.com/",
  "resolvedBy": "0x6A9D222616C90FcA5754cd1333cFD9b7fb6a4F74",
  "restricted": true,
  "rewardsMaxSpread": 0,
  "rewardsMinSize": 0,
  "rfqEnabled": false,
  "secondsDelay": 3,
  "sentDiscord": true,
  "slug": "mlb-wsh-nym-2025-06-10",
  "spread": 1,
  "startDate": "2025-06-09T08:01:34.856648Z",
  "startDateIso": "2025-06-09",
  "umaResolutionStatuses": "[]",
  "updatedAt": "2025-06-09T09:08:16.234902Z",
  "wideFormat": true
}
"""