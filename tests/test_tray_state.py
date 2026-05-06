"""
Unit tests for tray menu state and keyboard hook pause/resume.
pystray and keyboard library are fully mocked — no OS tray, no global hook.
"""
import sys
import pytest
from unittest.mock import MagicMock, patch

from textforge.app import TextForgeApp


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_app(credentials=None, user_email=None, hook_paused=False):
    """Minimal mock app object for tray menu inspection."""
    app = MagicMock()
    app.credentials = credentials
    app.user_email = user_email
    mock_hook = MagicMock()
    mock_hook.is_paused = hook_paused
    app.keyboard_hook = mock_hook
    return app


def _collect_menu_labels(app_mock):
    """
    Build tray with a fake pystray, call the dynamic menu callable,
    and return the list of MenuItem labels that were created.
    """
    labels = []

    class FakeMenuItem:
        def __init__(self, label, action=None, enabled=True, **kw):
            labels.append(label)

    class FakeMenu:
        SEPARATOR = object()

        def __init__(self, fn_or_items=None):
            if callable(fn_or_items):
                fn_or_items()  # trigger _menu_items() to populate labels

    fake_pystray = MagicMock()
    fake_pystray.MenuItem = FakeMenuItem
    fake_pystray.Menu = FakeMenu
    fake_pystray.Menu.SEPARATOR = FakeMenu.SEPARATOR
    fake_pystray.Icon = MagicMock(return_value=MagicMock())

    with patch.dict(sys.modules, {"pystray": fake_pystray}):
        from textforge.tray import build_tray_icon
        build_tray_icon(app_mock)

    return labels


# ── menu item presence ────────────────────────────────────────────────────────

def test_menu_signed_out_shows_sign_in_not_sign_out():
    app = _make_app(credentials=None)
    labels = _collect_menu_labels(app)
    assert "Sign In" in labels
    assert "Sign Out" not in labels


def test_menu_signed_in_shows_sign_out_not_sign_in():
    app = _make_app(credentials=MagicMock())
    labels = _collect_menu_labels(app)
    assert "Sign Out" in labels
    assert "Sign In" not in labels


def test_menu_signed_in_shows_email_in_account_label():
    app = _make_app(credentials=MagicMock(), user_email="bala@example.com")
    labels = _collect_menu_labels(app)
    account_labels = [l for l in labels if "bala@example.com" in l]
    assert len(account_labels) == 1


# ── toggle_pause via TextForgeApp ─────────────────────────────────────────────

def test_toggle_pause_when_running_calls_hook_pause():
    app = TextForgeApp()
    mock_hook = MagicMock()
    mock_hook.is_paused = False
    app.keyboard_hook = mock_hook
    app._tray_icon = None

    app.toggle_pause()

    mock_hook.pause.assert_called_once()
    mock_hook.resume.assert_not_called()


def test_toggle_pause_when_paused_calls_hook_resume():
    app = TextForgeApp()
    mock_hook = MagicMock()
    mock_hook.is_paused = True
    app.keyboard_hook = mock_hook
    app._tray_icon = None

    app.toggle_pause()

    mock_hook.resume.assert_called_once()
    mock_hook.pause.assert_not_called()


# ── KeyboardHook pause / resume internals ─────────────────────────────────────

def test_keyboard_hook_pause_sets_flag_and_calls_stop():
    mock_kb = MagicMock()
    with (
        patch.dict(sys.modules, {"keyboard": mock_kb}),
        patch("textforge.keyboard_hook.get_all_shortcuts", return_value={}),
    ):
        from textforge.keyboard_hook import KeyboardHook
        hook = KeyboardHook()
        hook.pause()

    assert hook.is_paused is True
    mock_kb.unhook_all.assert_called()


def test_keyboard_hook_resume_clears_flag_and_calls_start():
    mock_kb = MagicMock()
    with (
        patch.dict(sys.modules, {"keyboard": mock_kb}),
        patch("textforge.keyboard_hook.get_all_shortcuts", return_value={}),
    ):
        from textforge.keyboard_hook import KeyboardHook
        hook = KeyboardHook()
        hook._paused = True
        hook.resume()

    assert hook.is_paused is False
    mock_kb.on_press.assert_called()
