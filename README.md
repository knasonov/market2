# market2

This repository contains utilities for working with [Polymarket](https://polymarket.com).

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Retrieving Recent Markets

`get_recent_markets.py` fetches all markets created in the last 24 hours using Polymarket's public API. The script defaults to the new GraphQL endpoint `https://api.polymarket.xyz/graphql`. Set the `POLYMARKET_API_URL` environment variable to override the endpoint if it changes again.

Run the script with:

```bash
python get_recent_markets.py
```

The output lists market IDs, their slugs, and creation times. The script can be
imported as a module for further processing.
