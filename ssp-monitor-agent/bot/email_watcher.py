# bot/email_watcher.py
import email
import imaplib

_IMAP_HOST = "imap.gmail.com"
_SENDER = "airflow@kueez.com"


def fetch_latest_csv(gmail_email: str, app_password: str):
    """Return CSV string from the latest SSP report email, or None if not found."""
    with imaplib.IMAP4_SSL(_IMAP_HOST) as mail:
        mail.login(gmail_email, app_password)
        mail.select('"clients-alerts-ssp-revshare-group"')

        # Try unseen first, fall back to most recent from sender
        _, msg_ids = mail.search(None, f'FROM "{_SENDER}" UNSEEN')
        ids = msg_ids[0].split()

        if not ids:
            _, msg_ids = mail.search(None, f'FROM "{_SENDER}"')
            ids = msg_ids[0].split()
            if not ids:
                return None
            ids = [ids[-1]]

        _, msg_data = mail.fetch(ids[-1], "(RFC822)")
        raw = msg_data[0][1]
        mail.store(ids[-1], "+FLAGS", "\\Seen")

        msg = email.message_from_bytes(raw)
        for part in msg.walk():
            if part.get_content_type() == "text/csv" or (
                part.get_content_disposition() == "attachment"
                and (part.get_filename() or "").endswith(".csv")
            ):
                payload = part.get_payload(decode=True)
                return payload.decode("utf-8", errors="replace")

    return None
