from unittest import mock

import pytest

from src.config import settings
from src.utils.email import send_email


def test_send_email_without_smtp_only_logs():
    with mock.patch("smtplib.SMTP") as smtp:
        send_email("guest@example.com", "Тема", "Текст")
    smtp.assert_not_called()


def test_send_email_via_smtp(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_USER", "user")
    monkeypatch.setattr(settings, "SMTP_PASS", "pass")
    with mock.patch("smtplib.SMTP") as smtp:
        send_email("guest@example.com", "Тема", "Текст")

    smtp.assert_called_once_with("smtp.example.com", settings.SMTP_PORT, timeout=30)
    client = smtp.return_value.__enter__.return_value
    client.starttls.assert_called_once()
    client.login.assert_called_once_with("user", "pass")
    message = client.send_message.call_args.args[0]
    assert message["To"] == "guest@example.com"
    assert message["Subject"] == "Тема"
