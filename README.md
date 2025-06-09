# market2

This repository contains utilities for working with [Polymarket](https://polymarket.com).

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Retrieving Recent Markets

`get_recent_markets.py` fetches all markets created in the last 24 hours using Polymarket's public API.

Run the script with:

```bash
python get_recent_markets.py
```

The output lists market IDs, their slugs, and creation times. The script can be
imported as a module for further processing.
