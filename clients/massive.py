import os
from datetime import date
from typing import Any
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.polygon.io"
_API_KEY = os.getenv("MASSIVE_API_KEY")


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    p = {"apiKey": _API_KEY, **(params or {})}
    response = httpx.get(url, params=p, timeout=10)
    response.raise_for_status()
    return response.json()


def get_daily_bars(ticker: str, from_date: date, to_date: date) -> list[dict[str, Any]]:
    path = f"/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"
    data = _get(path, {"adjusted": "true", "sort": "asc"})
    return data.get("results", [])


def get_hourly_bars(ticker: str, from_date: date, to_date: date) -> list[dict[str, Any]]:
    path = f"/v2/aggs/ticker/{ticker}/range/1/hour/{from_date}/{to_date}"
    data = _get(path, {"adjusted": "true", "sort": "asc"})
    return data.get("results", [])


def get_snapshot(ticker: str) -> dict[str, Any]:
    path = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
    data = _get(path)
    return data.get("ticker", {})


def get_rsi(ticker: str, timespan: str = "day", window: int = 14) -> list[dict[str, Any]]:
    path = f"/v1/indicators/rsi/{ticker}"
    data = _get(path, {"timespan": timespan, "window": window, "limit": 10})
    return data.get("results", {}).get("values", [])


def get_macd(ticker: str, timespan: str = "day") -> list[dict[str, Any]]:
    path = f"/v1/indicators/macd/{ticker}"
    data = _get(path, {"timespan": timespan, "limit": 10})
    return data.get("results", {}).get("values", [])


def get_news(ticker: str, limit: int = 10) -> list[dict[str, Any]]:
    path = "/v2/reference/news"
    data = _get(path, {"ticker": ticker, "limit": limit, "order": "desc"})
    return data.get("results", [])


def get_options_chain(ticker: str) -> list[dict[str, Any]]:
    path = f"/v3/snapshot/options/{ticker}"
    data = _get(path, {"limit": 250})
    return data.get("results", [])


def get_nyse_tickers() -> list[str]:
    """Return all active common stocks (type=CS) listed on NYSE."""
    tickers: list[str] = []
    params = {"market": "stocks", "exchange": "XNYS", "type": "CS", "active": "true", "limit": 1000}
    data = _get("/v3/reference/tickers", params)
    while True:
        tickers.extend(r["ticker"] for r in data.get("results", []))
        next_url = data.get("next_url")
        if not next_url:
            break
        response = httpx.get(next_url, params={"apiKey": _API_KEY}, timeout=30)
        response.raise_for_status()
        data = response.json()
    return tickers
