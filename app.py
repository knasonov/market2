from typing import List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from get_recent_markets import fetch_latest

app = FastAPI(title="Polymarket Recent Markets")


@app.get("/api/markets")
def get_markets(limit: int = 50) -> List[Dict]:
    """Return the newest Polymarket markets."""
    try:
        return fetch_latest(limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve the front-end HTML page."""
    with open("static/index.html", "r", encoding="utf-8") as fh:
        return fh.read()


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
