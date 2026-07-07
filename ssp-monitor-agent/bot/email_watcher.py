# bot/email_watcher.py
import email
import imaplib

_IMAP_HOST = "imap.gmail.com"
_SENDER = "airflow@kueez.com"
_LABEL = '"clients-alerts-ssp-revshare-group"'


def fetch_latest_csv(gmail_email: str, app_password: str):
    """Return CSV string from the latest SSP report email, or None if not found."""
    with imaplib.IMAP4_SSL(_IMAP_HOST) as mail:
        mail.login(gmail_email, app_password)

        # Try the SSP label first, fall back to INBOX
        for folder in (_LABEL, "INBOX"):
            try:
                mail.select(folder)
            except Exception:
                continue

            # Try unseen first, fall back to most recent from sender
            _, msg_ids = mail.search(None, f'FROM "{_SENDER}" UNSEEN')
            ids = msg_ids[0].split()

            if not ids:
                _, msg_ids = mail.search(None, f'FROM "{_SENDER}"')
                ids = msg_ids[0].split()

            if ids:
                _, msg_data = mail.fetch(ids[-1], "(RFC822)")
                raw = msg_data[0][1]
                mail.store(ids[-1], "+FLAGS", "\\Seen")

                msg = email.message_from_bytes(raw)

                # Try CSV attachment first
                for part in msg.walk():
                    if part.get_content_type() == "text/csv" or (
                        part.get_content_disposition() == "attachment"
                        and (part.get_filename() or "").endswith(".csv")
                    ):
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload.decode("utf-8", errors="replace")

                # Fall back to plain text body — extract lines with commas or tabs
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if not payload:
                            continue
                        text = payload.decode("utf-8", errors="replace")
                        lines = text.splitlines()
                        # Extract table lines (tab or comma separated, skip alert footer)
                        table_lines = [
                            l for l in lines
                            if ("\t" in l or "," in l)
                            and not l.startswith("Alert")
                            and not l.startswith("Rows:")
                            and not l.startswith("Breakdowns:")
                            and not l.startswith("Metrics:")
                            and not l.startswith("Filters:")
                            and not l.startswith("Conditions:")
                            and not l.startswith("Rules:")
                        ]
                        if table_lines:
                            return "\n".join(table_lines)

    return None
