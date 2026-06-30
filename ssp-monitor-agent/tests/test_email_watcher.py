# tests/test_email_watcher.py
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

from bot.email_watcher import fetch_latest_csv


def _make_email_bytes(csv_content: str) -> bytes:
    msg = MIMEMultipart()
    msg["From"] = "airflow@kueez.com"
    msg["Subject"] = "[BEUI Alert]: SSP Last 30 days - New 2026"
    part = MIMEBase("text", "csv")
    part.set_payload(csv_content.encode())
    part.add_header("Content-Disposition", "attachment", filename="report.csv")
    msg.attach(part)
    return msg.as_bytes()


def _mock_imap(raw_email_bytes: bytes, has_unseen: bool = True):
    mock_mail = MagicMock()
    mock_mail.login.return_value = ("OK", [])
    mock_mail.select.return_value = ("OK", [])
    if has_unseen:
        mock_mail.search.return_value = ("OK", [b"1"])
    else:
        mock_mail.search.return_value = ("OK", [b""])
    mock_mail.fetch.return_value = ("OK", [(b"1 (RFC822 {100})", raw_email_bytes)])
    mock_mail.store.return_value = ("OK", [])

    mock_class = MagicMock()
    mock_class.return_value.__enter__ = MagicMock(return_value=mock_mail)
    mock_class.return_value.__exit__ = MagicMock(return_value=False)
    return mock_class, mock_mail


def test_fetch_returns_csv_content():
    raw = _make_email_bytes("col1,col2\nval1,val2")
    mock_class, _ = _mock_imap(raw)
    with patch("bot.email_watcher.imaplib.IMAP4_SSL", mock_class):
        result = fetch_latest_csv("test@gmail.com", "apppass")
    assert "col1,col2" in result


def test_fetch_marks_email_as_read():
    raw = _make_email_bytes("a,b\n1,2")
    mock_class, mock_mail = _mock_imap(raw)
    with patch("bot.email_watcher.imaplib.IMAP4_SSL", mock_class):
        fetch_latest_csv("test@gmail.com", "apppass")
    mock_mail.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")


def test_fetch_returns_none_when_no_email():
    mock_mail = MagicMock()
    mock_mail.login.return_value = ("OK", [])
    mock_mail.select.return_value = ("OK", [])
    mock_mail.search.return_value = ("OK", [b""])

    mock_class = MagicMock()
    mock_class.return_value.__enter__ = MagicMock(return_value=mock_mail)
    mock_class.return_value.__exit__ = MagicMock(return_value=False)

    with patch("bot.email_watcher.imaplib.IMAP4_SSL", mock_class):
        result = fetch_latest_csv("test@gmail.com", "apppass")
    assert result is None
