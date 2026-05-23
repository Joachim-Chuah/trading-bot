from unittest.mock import patch, MagicMock
import clients.email_client as email_module


def test_send_report_sends_email(monkeypatch):
    monkeypatch.setattr(email_module, "_USER", "test@gmail.com")
    monkeypatch.setattr(email_module, "_PASSWORD", "test-password")

    mock_smtp = MagicMock()
    with patch("clients.email_client.smtplib.SMTP_SSL") as mock_ssl:
        mock_ssl.return_value.__enter__.return_value = mock_smtp
        from clients.email_client import send_report
        send_report("Test Subject", "Report body", "report.txt")

    mock_smtp.login.assert_called_once_with("test@gmail.com", "test-password")
    mock_smtp.send_message.assert_called_once()


def test_send_report_includes_raw_data_in_attachment(monkeypatch):
    monkeypatch.setattr(email_module, "_USER", "test@gmail.com")
    monkeypatch.setattr(email_module, "_PASSWORD", "test-password")

    mock_smtp = MagicMock()
    with patch("clients.email_client.smtplib.SMTP_SSL") as mock_ssl:
        mock_ssl.return_value.__enter__.return_value = mock_smtp
        from clients.email_client import send_report
        msg_captured = []
        mock_smtp.send_message.side_effect = lambda m: msg_captured.append(m)
        send_report("Subject", "Narrative", "report.txt", raw_data="RAW")

    payload = msg_captured[0].get_payload()
    attachment_text = payload[1].get_payload(decode=True).decode()
    assert "=== MARKET ANALYSIS ===" in attachment_text
    assert "Narrative" in attachment_text
    assert "=== SOURCE DATA ===" in attachment_text
    assert "RAW" in attachment_text


def test_send_report_skips_when_no_credentials(monkeypatch):
    monkeypatch.setattr(email_module, "_USER", None)
    monkeypatch.setattr(email_module, "_PASSWORD", None)

    with patch("clients.email_client.smtplib.SMTP_SSL") as mock_ssl:
        from clients.email_client import send_report
        send_report("Test Subject", "Report body", "report.txt")

    mock_ssl.assert_not_called()
