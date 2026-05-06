"""
Unit tests for Drive sync: sync_from_drive, sync_to_drive, and the periodic
sync loop in TextForgeApp. No real Drive API calls — all mocked.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from textforge.drive_sync import sync_from_drive, sync_to_drive
from textforge.app import TextForgeApp


# ── sync_from_drive ───────────────────────────────────────────────────────────

def test_sync_from_drive_returns_false_on_api_exception():
    mock_creds = MagicMock()
    with patch("textforge.drive_sync.get_drive_service",
               side_effect=Exception("network error")):
        result = sync_from_drive(mock_creds)
    assert result is False


def test_sync_from_drive_returns_false_when_download_fails():
    mock_creds = MagicMock()
    mock_service = MagicMock()
    with (
        patch("textforge.drive_sync.get_drive_service", return_value=mock_service),
        patch("textforge.drive_sync.find_snippets_file", return_value="file123"),
        patch("textforge.drive_sync.download_snippets",
              side_effect=Exception("download error")),
    ):
        result = sync_from_drive(mock_creds)
    assert result is False


def test_sync_from_drive_saves_remote_data_locally():
    mock_creds = MagicMock()
    mock_service = MagicMock()
    remote_data = {
        "version": 1,
        "snippets": [{"id": "abc", "shortcut": "bs", "expansion": "Balaji"}],
    }
    with (
        patch("textforge.drive_sync.get_drive_service", return_value=mock_service),
        patch("textforge.drive_sync.find_snippets_file", return_value="file123"),
        patch("textforge.drive_sync.download_snippets", return_value=remote_data),
        patch("textforge.drive_sync._save_raw") as mock_save,
    ):
        result = sync_from_drive(mock_creds)

    assert result is True
    mock_save.assert_called_once_with(remote_data)


# ── sync_to_drive ─────────────────────────────────────────────────────────────

def test_sync_to_drive_returns_true_when_local_empty():
    mock_creds = MagicMock()
    with patch("textforge.drive_sync._load_raw", return_value={}):
        result = sync_to_drive(mock_creds)
    assert result is True


def test_sync_to_drive_returns_false_on_api_exception():
    mock_creds = MagicMock()
    local_data = {"version": 1, "snippets": [{"shortcut": "bs"}]}
    with (
        patch("textforge.drive_sync._load_raw", return_value=local_data),
        patch("textforge.drive_sync.get_drive_service",
              side_effect=Exception("auth error")),
    ):
        result = sync_to_drive(mock_creds)
    assert result is False


def test_sync_to_drive_returns_true_on_success():
    mock_creds = MagicMock()
    mock_service = MagicMock()
    local_data = {"version": 1, "snippets": [{"shortcut": "bs"}]}
    with (
        patch("textforge.drive_sync._load_raw", return_value=local_data),
        patch("textforge.drive_sync.get_drive_service", return_value=mock_service),
        patch("textforge.drive_sync.find_snippets_file", return_value="file123"),
        patch("textforge.drive_sync.upload_snippets", return_value="file123"),
    ):
        result = sync_to_drive(mock_creds)
    assert result is True


# ── periodic sync loop in TextForgeApp ────────────────────────────────────────

def test_periodic_sync_calls_both_sync_functions_when_signed_in():
    app = TextForgeApp()
    app.credentials = MagicMock()
    app.keyboard_hook = MagicMock()
    app._main_window = None
    app._sync_timer = None

    with (
        patch("textforge.drive_sync.sync_to_drive") as mock_push,
        patch("textforge.drive_sync.sync_from_drive") as mock_pull,
        patch.object(app, "_schedule_sync"),   # don't start a real timer
        patch.object(app, "_update_sync_label"),
    ):
        app._periodic_sync()

    mock_push.assert_called_once_with(app.credentials)
    mock_pull.assert_called_once_with(app.credentials)
