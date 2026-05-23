import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from clients.yfinance_client import get_vix, get_price_history


def mock_ticker(df: pd.DataFrame) -> MagicMock:
    m = MagicMock()
    m.history.return_value = df
    return m


@patch("clients.yfinance_client.yf.Ticker")
def test_get_vix_returns_dataframe(mock_ticker_cls):
    df = pd.DataFrame({"Close": [22.4, 21.8, 23.1]})
    mock_ticker_cls.return_value = mock_ticker(df)
    result = get_vix()
    assert isinstance(result, pd.DataFrame)
    assert "Close" in result.columns


@patch("clients.yfinance_client.yf.Ticker")
def test_get_vix_uses_vix_ticker(mock_ticker_cls):
    mock_ticker_cls.return_value = mock_ticker(pd.DataFrame({"Close": [22.4]}))
    get_vix()
    mock_ticker_cls.assert_called_once_with("^VIX")


@patch("clients.yfinance_client.yf.Ticker")
def test_get_vix_empty(mock_ticker_cls):
    mock_ticker_cls.return_value = mock_ticker(pd.DataFrame())
    result = get_vix()
    assert result.empty


@patch("clients.yfinance_client.yf.Ticker")
def test_get_price_history(mock_ticker_cls):
    df = pd.DataFrame({"Close": [190.0, 192.0, 194.5]})
    mock_ticker_cls.return_value = mock_ticker(df)
    result = get_price_history("AAPL")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3


@patch("clients.yfinance_client.yf.Ticker")
def test_get_price_history_uses_ticker(mock_ticker_cls):
    mock_ticker_cls.return_value = mock_ticker(pd.DataFrame({"Close": [190.0]}))
    get_price_history("NVDA", period="5y")
    mock_ticker_cls.assert_called_once_with("NVDA")
