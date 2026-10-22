"""
gmail_tool.py — Gmail send_email implementation using the Gmail API.
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Union

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google_auth import get_credentials

logger = logging.getLogger(__name__)


def send_email(
    to: Union[str, list[str]],
    subject: str,
    body: str,
    cc: Union[str, list[str], None] = None,
    bcc: Union[str, list[str], None] = None,
    is_html: bool = False,
) -> dict:
    """
    Send an email using the authenticated Gmail account.

    Args:
        to:      Recipient address(es).
        subject: Email subject.
        body:    Email body (plain text or HTML).
        cc:      Optional CC address(es).
        bcc:     Optional BCC address(es).
        is_html: If True, send body as text/html; otherwise text/plain.

    Returns:
        dict with keys: messageId, threadId, labelIds
    """
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    # Normalise recipients to comma-joined strings
    def _join(val: Union[str, list[str], None]) -> str:
        if val is None:
            return ""
        if isinstance(val, list):
            return ", ".join(val)
        return val

    mime_type = "html" if is_html else "plain"

    # Build the MIME message
    if cc or bcc:
        msg = MIMEMultipart("alternative")
        msg["To"] = _join(to)
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = _join(cc)
        if bcc:
            msg["Bcc"] = _join(bcc)
        msg.attach(MIMEText(body, mime_type, "utf-8"))
    else:
        msg = MIMEText(body, mime_type, "utf-8")
        msg["To"] = _join(to)
        msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    try:
        result = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
    except HttpError as exc:
        logger.error("Gmail API error: %s", exc)
        raise RuntimeError(f"Gmail API error {exc.resp.status}: {exc.reason}") from exc

    logger.info("Email sent — messageId=%s", result.get("id"))
    return {
        "messageId": result.get("id", ""),
        "threadId": result.get("threadId", ""),
        "labelIds": result.get("labelIds", []),
    }
