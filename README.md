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

Or simply run the application module directly:

```bash
python app.py
```

Then open `http://localhost:8000/` in your browser.

## Checking Market Prices

`market_prices.py` prints the best bid and ask for each outcome of a Polymarket
market. The script accepts either a full condition ID (the long hexadecimal
string used by the CLOB API) or the shorter numeric market ID that appears in
the Polymarket UI. When a numeric ID is provided, the tool searches the most
recent markets using `get_recent_markets.py` to resolve it to the corresponding
condition ID.

```bash
python market_prices.py 550868      # numeric ID
python market_prices.py 0xabc...    # condition ID
```
