import json
import logging
import urllib.request
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import CLIENT_SECRETS_FILE, TOKEN_FILE, APPDATA_DIR, SCOPES

log = logging.getLogger(__name__)


def get_credentials() -> Credentials | None:
    """
    Load credentials from TOKEN_FILE if they exist.
    Refresh if expired. Return None if no token file exists.
    """
    if not TOKEN_FILE.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    except Exception as e:
        log.warning("Failed to load token file: %s", e)
        return None

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
            return creds
        except RefreshError as e:
            log.warning("Token refresh failed: %s", e)
            return None

    return None


def run_oauth_flow() -> Credentials:
    """
    Start local HTTP server on a random port.
    Open browser to OAuth consent URL.
    Wait for redirect callback with code.
    Exchange code for tokens.
    Save to TOKEN_FILE.
    Return credentials.
    """
    if not CLIENT_SECRETS_FILE.exists():
        raise FileNotFoundError(
            f"client_secrets.json not found at {CLIENT_SECRETS_FILE}.\n"
            "Please follow docs/02-google-oauth-setup.md to create it."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRETS_FILE), scopes=SCOPES
    )
    creds = flow.run_local_server(port=0, prompt="consent")
    _save_credentials(creds)
    return creds


def _save_credentials(creds: Credentials) -> None:
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")


def get_user_email(credentials: Credentials) -> str:
    """
    Return the signed-in user's email address.
    Tries googleapiclient first; falls back to a direct urllib call so
    it works in PyInstaller bundles where discovery docs may be missing.
    """
    # Primary: googleapiclient discovery
    try:
        service = build("oauth2", "v2", credentials=credentials)
        info = service.userinfo().get().execute()
        email = info.get("email", "")
        if email:
            return email
    except Exception as e:
        log.debug("googleapiclient userinfo failed, trying urllib fallback: %s", e)

    # Fallback: direct HTTPS call — no discovery docs needed
    try:
        req = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("email", "")
    except Exception as e:
        log.warning("get_user_email fallback also failed: %s", e)
        return ""


def sign_out() -> None:
    """Delete TOKEN_FILE. Attempt to revoke token from Google."""
    if not TOKEN_FILE.exists():
        return

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds.token:
            urllib.request.urlopen(
                f"https://oauth2.googleapis.com/revoke?token={creds.token}",
                timeout=5,
            )
    except Exception as e:
        log.debug("Token revocation failed (non-fatal): %s", e)

    try:
        TOKEN_FILE.unlink()
    except OSError as e:
        log.warning("Failed to delete token file: %s", e)


def is_signed_in() -> bool:
    """Return True if TOKEN_FILE exists and has a refresh token."""
    if not TOKEN_FILE.exists():
        return False
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        return bool(data.get("refresh_token"))
    except Exception as e:
        log.debug("Failed to read token file for sign-in check: %s", e)
        return False
