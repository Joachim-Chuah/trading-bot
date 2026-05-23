import os
from typing import Any
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://financialmodelingprep.com/stable"
_API_KEY = os.getenv("FMP_API_KEY")


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{BASE_URL}{path}"
    p = {"apikey": _API_KEY, **(params or {})}
    response = httpx.get(url, params=p, timeout=10)
    response.raise_for_status()
    return response.json()


def get_profile(ticker: str) -> dict[str, Any]:
    data = _get("/profile", {"symbol": ticker})
    return data[0] if data else {}


def get_ratios(ticker: str) -> dict[str, Any]:
    data = _get("/ratios", {"symbol": ticker, "limit": 1})
    return data[0] if data else {}


def get_income_statement(ticker: str) -> dict[str, Any]:
    data = _get("/income-statement", {"symbol": ticker, "limit": 1})
    return data[0] if data else {}


def get_key_metrics(ticker: str) -> dict[str, Any]:
    data = _get("/key-metrics", {"symbol": ticker, "limit": 1})
    return data[0] if data else {}


def get_stock_screener(sector: str, min_market_cap: int = 2_000_000_000) -> list[dict[str, Any]]:
    data = _get("/stock-screener", {
        "sector": sector,
        "marketCapMoreThan": min_market_cap,
        "isActivelyTrading": "true",
        "limit": 200,
    })
    return data if isinstance(data, list) else []
