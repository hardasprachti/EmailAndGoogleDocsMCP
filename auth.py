"""
auth.py — First-time OAuth 2.0 consent flow for Gmail + Google Docs.

Priority order for credentials:
  1. credentials.json  (downloaded from Google Cloud Console — preferred)
  2. .env file         (GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET)

Run this once to generate token.json before starting the MCP server.
"""

import json
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents",
]

_ROOT = Path(__file__).parent
CREDENTIALS_FILE = _ROOT / "credentials.json"
TOKEN_FILE = _ROOT / "token.json"
ENV_FILE = _ROOT / ".env"


def _load_env() -> dict:
    """Parse key=value pairs from .env (ignores comments and blank lines)."""
    env: dict = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip()
    return env


def _build_credentials_from_env(env: dict) -> dict | None:
    """
    Construct the credentials.json structure from .env variables.
    Returns None if required keys are missing or empty.
    """
    client_id = env.get("GOOGLE_CLIENT_ID", "")
    client_secret = env.get("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def main() -> None:
    # ── Resolve credentials source ────────────────────────────────────────
    if CREDENTIALS_FILE.exists():
        print(f"[OK] Using credentials from {CREDENTIALS_FILE}")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)

    else:
        env = _load_env()
        cred_dict = _build_credentials_from_env(env)

        if cred_dict is None:
            print(
                "ERROR: No credentials found.\n"
                "\n"
                "Option A — Download credentials.json from Google Cloud Console\n"
                "           and place it in the project root.\n"
                "\n"
                "Option B — Fill in GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET\n"
                "           in your .env file.",
                file=sys.stderr,
            )
            sys.exit(1)

        print("[OK] Using credentials from .env (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET)")
        flow = InstalledAppFlow.from_client_config(cred_dict, SCOPES)

    # ── Run consent flow ──────────────────────────────────────────────────
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())
    print(f"[OK] Token saved to {TOKEN_FILE}")
    print("You can now start the MCP server with:  python server.py")


if __name__ == "__main__":
    main()
