"""
google_auth.py — Shared Google OAuth2 credential management.

Loads credentials from the GOOGLE_TOKEN_JSON env var (hosted deployments) or,
failing that, from token.json, and auto-refreshes when expired.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents",
]

_CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
_TOKEN_FILE = Path(__file__).parent / "token.json"

# Module-level cached credentials
_creds: Optional[Credentials] = None


def get_credentials() -> Credentials:
    """
    Return valid Google OAuth2 credentials, refreshing the token if needed.
    Raises RuntimeError if credentials cannot be obtained.
    """
    global _creds

    if _creds and _creds.valid:
        return _creds

    token_json = os.environ.get("GOOGLE_TOKEN_JSON", "").strip()
    from_env = bool(token_json)

    # Reuse the cached object when it only needs a refresh; otherwise load fresh.
    if not _creds:
        if from_env:
            _creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        elif _TOKEN_FILE.exists():
            _creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), SCOPES)
        else:
            _raise_no_token()

    if not _creds or not _creds.valid:
        if _creds and _creds.expired and _creds.refresh_token:
            logger.info("Refreshing expired Google OAuth2 token...")
            _creds.refresh(Request())
            if from_env:
                # Env vars can't be written back; the refreshed access token stays in
                # memory and the refresh token in the env var is reused after restarts.
                logger.info("Token refreshed (in memory).")
            else:
                # Persist the refreshed token
                _TOKEN_FILE.write_text(_creds.to_json())
                logger.info("Token refreshed and saved.")
        else:
            _raise_no_token()

    return _creds


def _raise_no_token() -> None:
    raise RuntimeError(
        "Google credentials not found or invalid.\n"
        "Set GOOGLE_TOKEN_JSON, or run:  python auth.py\n"
        "to complete the one-time OAuth2 consent flow."
    )
