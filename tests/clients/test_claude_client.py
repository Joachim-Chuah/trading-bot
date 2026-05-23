from unittest.mock import MagicMock, patch
import clients.claude_client as claude_module


def test_generate_report_calls_api(monkeypatch):
    monkeypatch.setattr(claude_module, "_API_KEY", "test-key")

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Market analysis report")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("clients.claude_client.anthropic.Anthropic", return_value=mock_client):
        from clients.claude_client import generate_report
        result = generate_report("raw screener output", report_type="research")

    assert result == "Market analysis report"
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert "raw screener output" in call_kwargs["messages"][0]["content"]


def test_generate_report_falls_back_without_api_key(monkeypatch):
    monkeypatch.setattr(claude_module, "_API_KEY", None)

    with patch("clients.claude_client.anthropic.Anthropic") as mock_anthropic:
        from clients.claude_client import generate_report
        result = generate_report("raw output", report_type="research")

    mock_anthropic.assert_not_called()
    assert result == "raw output"


def test_generate_report_uses_backtest_prompt(monkeypatch):
    monkeypatch.setattr(claude_module, "_API_KEY", "test-key")

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Backtest report")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("clients.claude_client.anthropic.Anthropic", return_value=mock_client):
        from clients.claude_client import generate_report
        generate_report("raw output", report_type="backtest")

    content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "LEAP options strategy" in content
