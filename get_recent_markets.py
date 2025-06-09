import requests
from datetime import datetime, timedelta, timezone

import os

# The public GraphQL endpoint occasionally moves.  Allow users to specify a
# preferred URL via the ``POLYMARKET_API_URL`` environment variable while
# providing a couple of sensible fallbacks.  ``API_URLS`` is a list so we can
# try each endpoint until one succeeds.
DEFAULT_API_URLS = [
    "https://api.polymarket.xyz/graphql",
    # An alternative endpoint that has been used in the past.  Requests will
    # fall back to this if the primary one fails.
    "https://polymarket.com/api/graphql",
]

env_url = os.getenv("POLYMARKET_API_URL")
API_URLS = [env_url] if env_url else DEFAULT_API_URLS

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

    last_exc = None
    for url in API_URLS:
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data["data"]["markets"]
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            continue

    raise SystemExit(
        f"Failed to fetch markets from available endpoints: {last_exc}"
    )


def main():
    markets = get_recent_markets()
    for market in markets:
        print(f"{market['id']}: {market['slug']} (created {market['creationTime']})")


if __name__ == "__main__":
    main()
