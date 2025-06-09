import requests
from datetime import datetime, timedelta, timezone

import os

# Polymarket moved its public GraphQL endpoint to a new domain. Allow overriding
# the endpoint via the ``POLYMARKET_API_URL`` environment variable so that users
# can easily update it in the future without modifying the code.
API_URL = os.getenv("POLYMARKET_API_URL", "https://api.polymarket.xyz/graphql")

QUERY = """
query($after: Int!) {
  markets(
    limit: 100,
    sortBy: "creationTime",
    sortDirection: "desc",
    filter: {creationTime: {gt: $after}}
  ) {
    id
    slug
    question
    description
    category
    subcategory
    outcomeType
    volume
    liquidity
    creationTime
    url
  }
}
"""

def get_recent_markets(hours=24):
    """Return markets created within the last `hours` hours."""
    created_after = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    payload = {
        "query": QUERY,
        "variables": {"after": created_after},
    }

    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise SystemExit(f"Failed to fetch markets: {exc}") from exc

    data = response.json()
    return data["data"]["markets"]


def main():
    markets = get_recent_markets()
    for market in markets:
        print(f"{market['id']}: {market['slug']} (created {market['creationTime']})")


if __name__ == "__main__":
    main()
