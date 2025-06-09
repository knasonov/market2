import requests
from datetime import datetime, timedelta, timezone

API_URL = "https://client-api.polymarket.com/graphql"

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

    response = requests.post(API_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["data"]["markets"]


def main():
    markets = get_recent_markets()
    for market in markets:
        print(f"{market['id']}: {market['slug']} (created {market['creationTime']})")


if __name__ == "__main__":
    main()
