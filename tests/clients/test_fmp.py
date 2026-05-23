import pytest
from unittest.mock import patch, MagicMock
from clients.fmp import get_profile, get_ratios, get_income_statement, get_key_metrics


def mock_response(payload) -> MagicMock:
    m = MagicMock()
    m.json.return_value = payload
    m.raise_for_status.return_value = None
    return m


@patch("clients.fmp.httpx.get")
def test_get_profile(mock_get):
    mock_get.return_value = mock_response([{"symbol": "AAPL", "mktCap": 3100000000000, "sector": "Technology"}])
    result = get_profile("AAPL")
    assert result["symbol"] == "AAPL"
    assert result["mktCap"] == 3100000000000


@patch("clients.fmp.httpx.get")
def test_get_profile_empty(mock_get):
    mock_get.return_value = mock_response([])
    result = get_profile("AAPL")
    assert result == {}


@patch("clients.fmp.httpx.get")
def test_get_ratios(mock_get):
    mock_get.return_value = mock_response([{"symbol": "AAPL", "peRatio": 28.5, "debtEquityRatio": 1.5}])
    result = get_ratios("AAPL")
    assert result["peRatio"] == 28.5


@patch("clients.fmp.httpx.get")
def test_get_ratios_empty(mock_get):
    mock_get.return_value = mock_response([])
    result = get_ratios("AAPL")
    assert result == {}


@patch("clients.fmp.httpx.get")
def test_get_income_statement(mock_get):
    mock_get.return_value = mock_response([{"symbol": "AAPL", "revenue": 394330000000, "eps": 6.43}])
    result = get_income_statement("AAPL")
    assert result["eps"] == 6.43


@patch("clients.fmp.httpx.get")
def test_get_income_statement_empty(mock_get):
    mock_get.return_value = mock_response([])
    result = get_income_statement("AAPL")
    assert result == {}


@patch("clients.fmp.httpx.get")
def test_get_key_metrics(mock_get):
    mock_get.return_value = mock_response([{"symbol": "AAPL", "revenuePerShare": 25.1, "roe": 1.47}])
    result = get_key_metrics("AAPL")
    assert result["roe"] == 1.47


@patch("clients.fmp.httpx.get")
def test_get_key_metrics_empty(mock_get):
    mock_get.return_value = mock_response([])
    result = get_key_metrics("AAPL")
    assert result == {}
