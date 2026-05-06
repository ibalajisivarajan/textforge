"""
Unit tests for auth state: is_signed_in, sign_out, get_user_email.
No real OAuth flows, no network calls — all external dependencies mocked.
"""
import json
import sys
import pytest
from unittest.mock import MagicMock, patch

from textforge.auth import is_signed_in, sign_out, get_user_email


# ── is_signed_in ──────────────────────────────────────────────────────────────

def test_is_signed_in_missing_file(tmp_path):
    token_file = tmp_path / "token.json"
    with patch("textforge.auth.TOKEN_FILE", token_file):
        assert is_signed_in() is False


def test_is_signed_in_no_refresh_token(tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({"token": "abc", "scopes": []}))
    with patch("textforge.auth.TOKEN_FILE", token_file):
        assert is_signed_in() is False


def test_is_signed_in_with_refresh_token(tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({"refresh_token": "rtoken123"}))
    with patch("textforge.auth.TOKEN_FILE", token_file):
        assert is_signed_in() is True


# ── sign_out ──────────────────────────────────────────────────────────────────

def test_sign_out_is_noop_when_no_token_file(tmp_path):
    token_file = tmp_path / "token.json"
    with patch("textforge.auth.TOKEN_FILE", token_file):
        sign_out()  # must not raise


def test_sign_out_deletes_token_file(tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({
        "token": "mytoken",
        "refresh_token": "rtoken",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "cid",
        "client_secret": "csecret",
        "scopes": ["https://www.googleapis.com/auth/drive.appdata"],
    }))
    with (
        patch("textforge.auth.TOKEN_FILE", token_file),
        patch("textforge.auth.urllib.request.urlopen"),  # skip network revoke
    ):
        sign_out()

    assert not token_file.exists()


# ── get_user_email ────────────────────────────────────────────────────────────

def test_get_user_email_via_googleapiclient():
    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.userinfo.return_value.get.return_value.execute.return_value = {
        "email": "test@example.com"
    }

    with patch("textforge.auth.build", return_value=mock_service):
        email = get_user_email(mock_creds)

    assert email == "test@example.com"


def test_get_user_email_falls_back_to_urllib():
    mock_creds = MagicMock()
    mock_creds.token = "mytoken"

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {"email": "fallback@example.com"}
    ).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with (
        patch("textforge.auth.build", side_effect=Exception("discovery failed")),
        patch("textforge.auth.urllib.request.urlopen", return_value=mock_response),
    ):
        email = get_user_email(mock_creds)

    assert email == "fallback@example.com"
