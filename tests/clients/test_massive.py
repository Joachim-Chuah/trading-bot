import pytest
from unittest.mock import patch, MagicMock
from clients.massive import (
    get_daily_bars,
    get_hourly_bars,
    get_snapshot,
    get_rsi,
    get_macd,
    get_news,
    get_options_chain,
)
from datetime import date


def mock_response(payload: dict) -> MagicMock:
    m = MagicMock()
    m.json.return_value = payload
    m.raise_for_status.return_value = None
    return m


@patch("clients.massive.httpx.get")
def test_get_daily_bars(mock_get):
    mock_get.return_value = mock_response({"results": [{"o": 190.0, "h": 195.0, "l": 188.0, "c": 193.0, "v": 1000000}]})
    result = get_daily_bars("AAPL", date(2026, 5, 1), date(2026, 5, 21))
    assert len(result) == 1
    assert result[0]["c"] == 193.0


@patch("clients.massive.httpx.get")
def test_get_daily_bars_empty(mock_get):
    mock_get.return_value = mock_response({})
    result = get_daily_bars("AAPL", date(2026, 5, 1), date(2026, 5, 21))
    assert result == []


@patch("clients.massive.httpx.get")
def test_get_hourly_bars(mock_get):
    mock_get.return_value = mock_response({"results": [{"o": 190.0, "c": 192.0, "v": 50000}]})
    result = get_hourly_bars("AAPL", date(2026, 5, 21), date(2026, 5, 21))
    assert len(result) == 1
    assert result[0]["o"] == 190.0


@patch("clients.massive.httpx.get")
def test_get_snapshot(mock_get):
    mock_get.return_value = mock_response({"ticker": {"ticker": "AAPL", "day": {"c": 194.5}}})
    result = get_snapshot("AAPL")
    assert result["ticker"] == "AAPL"
    assert result["day"]["c"] == 194.5


@patch("clients.massive.httpx.get")
def test_get_snapshot_empty(mock_get):
    mock_get.return_value = mock_response({})
    result = get_snapshot("AAPL")
    assert result == {}


@patch("clients.massive.httpx.get")
def test_get_rsi(mock_get):
    mock_get.return_value = mock_response({"results": {"values": [{"value": 32.5}, {"value": 35.0}]}})
    result = get_rsi("AAPL")
    assert len(result) == 2
    assert result[0]["value"] == 32.5


@patch("clients.massive.httpx.get")
def test_get_rsi_empty(mock_get):
    mock_get.return_value = mock_response({"results": {}})
    result = get_rsi("AAPL")
    assert result == []


@patch("clients.massive.httpx.get")
def test_get_macd(mock_get):
    mock_get.return_value = mock_response({"results": {"values": [{"value": -1.2, "signal": -0.8, "histogram": -0.4}]}})
    result = get_macd("AAPL")
    assert result[0]["value"] == -1.2


@patch("clients.massive.httpx.get")
def test_get_news(mock_get):
    mock_get.return_value = mock_response({
        "results": [
            {
                "title": "Apple beats earnings",
                "published_utc": "2026-05-21T10:00:00Z",
                "insights": [{"sentiment": "positive", "sentiment_reasoning": "Beat estimates"}],
            }
        ]
    })
    result = get_news("AAPL")
    assert len(result) == 1
    assert result[0]["title"] == "Apple beats earnings"
    assert result[0]["insights"][0]["sentiment"] == "positive"


@patch("clients.massive.httpx.get")
def test_get_news_empty(mock_get):
    mock_get.return_value = mock_response({"results": []})
    result = get_news("AAPL")
    assert result == []


@patch("clients.massive.httpx.get")
def test_get_options_chain(mock_get):
    mock_get.return_value = mock_response({
        "results": [
            {"details": {"strike_price": 195.0, "expiration_date": "2027-01-15"}, "greeks": {"delta": 0.55}}
        ]
    })
    result = get_options_chain("AAPL")
    assert len(result) == 1
    assert result[0]["details"]["strike_price"] == 195.0


@patch("clients.massive.httpx.get")
def test_get_options_chain_empty(mock_get):
    mock_get.return_value = mock_response({"results": []})
    result = get_options_chain("AAPL")
    assert result == []
