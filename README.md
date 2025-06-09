# market2

This repository contains utilities for working with [Polymarket](https://polymarket.com).

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Retrieving Recent Markets

`get_recent_markets.py` fetches all markets created in the last 24 hours using Polymarket's public API. The tool now tries a small list of known endpoints and will automatically fall back if the first one fails. You can override the list by setting the `POLYMARKET_API_URL` environment variable to a preferred endpoint.

Run the script with:

```bash
python get_recent_markets.py
```

The output lists market IDs, their slugs, and creation times. The script can be
imported as a module for further processing.

## Web Interface

A small FastAPI app exposes recent Polymarket markets and serves a simple HTML
page that lists the last 50 markets in a table.

Start the development server with:

```bash
uvicorn app:app --reload
```

Then open `http://localhost:8000/` in your browser.
