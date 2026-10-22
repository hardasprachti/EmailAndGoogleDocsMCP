"""
get_auth_url.py — Prints the Google OAuth2 authorization URL without opening a browser.
Copy the printed URL, paste it in your browser, complete sign-in, then paste the
redirect URL (localhost:...) back here when prompted.
"""

import json
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents",
]

_ROOT = Path(__file__).parent
ENV_FILE = _ROOT / ".env"
TOKEN_FILE = _ROOT / "token.json"
CREDENTIALS_FILE = _ROOT / "credentials.json"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def main():
    if CREDENTIALS_FILE.exists():
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    else:
        env = load_env()
        client_id = env.get("GOOGLE_CLIENT_ID", "")
        client_secret = env.get("GOOGLE_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            print("ERROR: No credentials found. Fill in .env or add credentials.json", file=sys.stderr)
            sys.exit(1)
        cred_dict = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(cred_dict, SCOPES)

    # Generate URL without opening browser
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    print("\n" + "=" * 70)
    print("STEP 1: Open this URL in your browser:")
    print("=" * 70)
    print(auth_url)
    print("=" * 70)
    print("\nSTEP 2: Sign in to Google and click Allow.")
    print("STEP 3: Copy the authorization code shown and paste it below.\n")

    code = input("Paste the authorization code here: ").strip()

    flow.fetch_token(code=code)
    creds = flow.credentials

    TOKEN_FILE.write_text(creds.to_json())
    print(f"\n[OK] Token saved to {TOKEN_FILE}")
    print("You can now start the MCP server with:  python server.py")


if __name__ == "__main__":
    main()
