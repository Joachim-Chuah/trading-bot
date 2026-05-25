import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_USER = os.getenv("GMAIL_USER")
_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_report(subject: str, body: str, filename: str, raw_data: str = "", chart_path: str = "") -> None:
    if not _USER or not _PASSWORD:
        return

    attachment = body
    if raw_data:
        attachment = f"=== MARKET ANALYSIS ===\n\n{body}\n\n=== SOURCE DATA ===\n\n{raw_data}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _USER
    msg["To"] = _USER
    msg.set_content(body)
    msg.add_attachment(attachment.encode(), maintype="text", subtype="plain", filename=filename)

    if chart_path:
        chart_bytes = Path(chart_path).read_bytes()
        msg.add_attachment(chart_bytes, maintype="image", subtype="png", filename=Path(chart_path).name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(_USER, _PASSWORD)
        smtp.send_message(msg)
