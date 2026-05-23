import pytest
from unittest.mock import patch, MagicMock
from clients.cboe import get_put_call_ratio


def mock_response(text: str, status: int = 200) -> MagicMock:
    m = MagicMock()
    m.text = text
    m.status_code = status
    m.raise_for_status.return_value = None
    return m


CBOE_HTML = """
<table>
  <tr><th>Category</th><th>P/C Ratio</th></tr>
  <tr><td>Equity</td><td>0.87</td></tr>
  <tr><td>Index</td><td>1.21</td></tr>
</table>
"""


@patch("clients.cboe.httpx.get")
def test_get_put_call_ratio_success(mock_get):
    mock_get.return_value = mock_response(CBOE_HTML)
    result = get_put_call_ratio()
    assert result == 0.87


@patch("clients.cboe.httpx.get")
def test_get_put_call_ratio_network_failure(mock_get):
    mock_get.side_effect = Exception("Connection error")
    result = get_put_call_ratio()
    assert result is None


@patch("clients.cboe.httpx.get")
def test_get_put_call_ratio_no_equity_row(mock_get):
    mock_get.return_value = mock_response("<table><tr><td>Index</td><td>1.21</td></tr></table>")
    result = get_put_call_ratio()
    assert result is None


@patch("clients.cboe.httpx.get")
def test_get_put_call_ratio_malformed_html(mock_get):
    mock_get.return_value = mock_response("<html><body>No table here</body></html>")
    result = get_put_call_ratio()
    assert result is None
